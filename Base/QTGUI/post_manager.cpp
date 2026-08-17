#include "post_manager.h"
#include "UserInfo.h"

#include <QNetworkRequest>
#include <QNetworkReply>
#include <QNetworkAccessManager>
#include <QUrl>
#include <QDebug>
#include <QJsonArray>
#include <QEventLoop>
#include <QUuid>

namespace
{
bool isZipArchiveHeader(const QByteArray& header)
{
  return header.size() >= 4 && header.startsWith("PK\x03\x04");
}

QString ctUploadFileName(const QString& ctFilePath)
{
  QString fileName = QFileInfo(ctFilePath).fileName();
  if (!fileName.endsWith(".nrrd", Qt::CaseInsensitive))
  {
    fileName += ".nrrd";
  }
  return fileName;
}

QString parseUploadErrorMessage(const QByteArray& responseData, int httpStatus)
{
  QJsonParseError jsonError;
  const QJsonDocument document = QJsonDocument::fromJson(responseData, &jsonError);
  if (document.isObject())
  {
    const QJsonObject obj = document.object();
    const QString msg = obj.value("msg").toString();
    if (!msg.isEmpty())
    {
      return msg;
    }

    const QJsonValue detailValue = obj.value("detail");
    if (detailValue.isString())
    {
      return detailValue.toString();
    }
    if (detailValue.isArray())
    {
      QStringList details;
      const QJsonArray detailArray = detailValue.toArray();
      for (const QJsonValue& item : detailArray)
      {
        if (item.isObject())
        {
          details << item.toObject().value("msg").toString();
        }
        else if (item.isString())
        {
          details << item.toString();
        }
      }
      if (!details.isEmpty())
      {
        return details.join("; ");
      }
    }
  }

  if (!responseData.isEmpty())
  {
    return QString::fromUtf8(responseData.left(512));
  }

  return QObject::tr("服务器返回错误 (HTTP %1)").arg(httpStatus);
}

void setErrorMessage(QString* errorMessage, const QString& message)
{
  if (errorMessage)
  {
    *errorMessage = message;
  }
}

bool validateZipFile(const QString& objZipPath, QString* errorMessage)
{
  QFile zipFile(objZipPath);
  if (!zipFile.open(QIODevice::ReadOnly))
  {
    qWarning() << "validateZipFile: cannot open" << objZipPath;
    setErrorMessage(errorMessage, QObject::tr("无法读取模型压缩包"));
    return false;
  }

  const QByteArray header = zipFile.read(4);
  const qint64 zipSize = zipFile.size();
  zipFile.close();

  if (zipSize <= 0 || !isZipArchiveHeader(header))
  {
    qWarning() << "validateZipFile: invalid zip" << objZipPath << "size:" << zipSize;
    setErrorMessage(errorMessage, QObject::tr("模型压缩包无效，请重新导出后再试"));
    return false;
  }
  return true;
}

bool validateCtFile(const QString& ctFilePath, qint64* ctSize, QString* errorMessage)
{
  QFileInfo ctInfo(ctFilePath);
  if (!ctInfo.exists() || !ctInfo.isFile())
  {
    setErrorMessage(errorMessage, QObject::tr("无法读取CT文件"));
    return false;
  }

  const qint64 size = ctInfo.size();
  if (size <= 0)
  {
    setErrorMessage(errorMessage, QObject::tr("CT文件为空"));
    return false;
  }

  if (ctSize)
  {
    *ctSize = size;
  }
  return true;
}

QString extractOrderIdFromResponse(const QByteArray& responseData)
{
  const QJsonDocument document = QJsonDocument::fromJson(responseData);
  if (!document.isObject())
  {
    return QString();
  }
  const QJsonObject root = document.object();
  const QJsonValue dataValue = root.value("data");
  if (dataValue.isObject())
  {
    const QJsonValue orderIdValue = dataValue.toObject().value("order_id");
    if (orderIdValue.isString())
    {
      return orderIdValue.toString();
    }
    if (orderIdValue.isDouble())
    {
      return QString::number(static_cast<qint64>(orderIdValue.toDouble()));
    }
  }
  return QString();
}

QByteArray readFileBytes(const QString& filePath, QString* errorMessage, const QString& errorText)
{
  QFile file(filePath);
  if (!file.open(QIODevice::ReadOnly))
  {
    setErrorMessage(errorMessage, errorText);
    return QByteArray();
  }
  const QByteArray data = file.readAll();
  file.close();
  if (data.isEmpty())
  {
    setErrorMessage(errorMessage, errorText);
  }
  return data;
}

void appendTextField(QByteArray& body, const QByteArray& boundary, const QString& name, const QByteArray& value)
{
  body += "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"" + name.toUtf8() + "\"\r\n\r\n";
  body += value;
  body += "\r\n";
}

void appendFileField(
  QByteArray& body,
  const QByteArray& boundary,
  const QString& fieldName,
  const QString& uploadFileName,
  const QByteArray& fileData)
{
  body += "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"" + fieldName.toUtf8()
        + "\"; filename=\"" + uploadFileName.toUtf8() + "\"\r\n";
  body += "Content-Type: application/octet-stream\r\n\r\n";
  body += fileData;
  body += "\r\n";
}

bool postByteArray(
  QNetworkAccessManager* manager,
  QNetworkReply*& reply,
  const QString& uploadUrl,
  const QByteArray& boundary,
  const QByteArray& body,
  QProgressDialog* progress,
  const QString& progressLabel,
  QString* errorMessage,
  QByteArray* responseOut)
{
  if (progress)
  {
    progress->setLabelText(progressLabel);
    progress->setValue(70);
    QApplication::processEvents();
  }

  QNetworkRequest request;
  request.setUrl(QUrl(uploadUrl));
  request.setHeader(
    QNetworkRequest::ContentTypeHeader,
    QVariant(QString("multipart/form-data; boundary=%1").arg(QString::fromLatin1(boundary))));

  qDebug() << "postByteArray url:" << uploadUrl << "body size:" << body.size();

  // 与 doPost / AI 上传相同：整包 QByteArray + manager->post + finished 事件循环
  reply = manager->post(request, body);

  QEventLoop eventLoop;
  QObject::connect(manager, SIGNAL(finished(QNetworkReply*)), &eventLoop, SLOT(quit()));
  eventLoop.exec();

  const QByteArray responseData = reply->readAll();
  const int httpStatus = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
  const bool networkOk = reply->error() == QNetworkReply::NoError;
  const bool success = networkOk && httpStatus >= 200 && httpStatus < 300;

  if (responseOut)
  {
    *responseOut = responseData;
  }

  qDebug() << "postByteArray done"
           << "qtError:" << reply->error()
           << reply->errorString()
           << "HTTP:" << httpStatus
           << "response:" << responseData;

  if (!success)
  {
    const QString responseError = networkOk
      ? parseUploadErrorMessage(responseData, httpStatus)
      : reply->errorString();
    setErrorMessage(errorMessage, responseError);
  }

  if (progress)
  {
    progress->setValue(success ? 100 : progress->value());
    QApplication::processEvents();
  }

  return success;
}
} // namespace

PostManager::PostManager(QWidget *parent)
    : QWidget{parent}
{
    manager = new QNetworkAccessManager(this);
}

void PostManager::doPost(QJsonObject json, QString postUrl) {

    QJsonDocument document;
    document.setObject(json);
    QByteArray dataArray = document.toJson(QJsonDocument::Compact);
    QNetworkRequest request;
    request.setUrl(QUrl(SERVER_URL + postUrl));
    request.setHeader(QNetworkRequest::ContentTypeHeader, QVariant("application/json"));

    reply = manager->post(request, dataArray);
    QEventLoop eventLoop;
    connect(manager, SIGNAL(finished(QNetworkReply*)), &eventLoop, SLOT(quit()));
    eventLoop.exec();

    QByteArray responseData = reply->readAll();

    QJsonParseError json_error;
    QJsonDocument doucment = QJsonDocument::fromJson(responseData, &json_error);
    const QJsonObject obj = doucment.object();
    emit postEnded( obj );
}

bool PostManager::uploadPatientOrderAll(
    const QString& receiver,
    const QString& objZipPath,
    const QString& ctFilePath,
    QProgressDialog* progress,
    QString* errorMessage)
{
    const QString uploadUrl = PATIENT_ORDER_UPLOAD_URL;

    if (receiver.trimmed().isEmpty())
    {
        setErrorMessage(errorMessage, QObject::tr("患者姓名不能为空"));
        return false;
    }
    if (!validateZipFile(objZipPath, errorMessage))
    {
        return false;
    }
    qint64 ctSize = 0;
    if (!validateCtFile(ctFilePath, &ctSize, errorMessage))
    {
        return false;
    }

    const QByteArray zipData = readFileBytes(
      objZipPath, errorMessage, QObject::tr("无法读取模型压缩包"));
    const QByteArray ctData = readFileBytes(
      ctFilePath, errorMessage, QObject::tr("无法读取CT文件"));
    if (zipData.isEmpty() || ctData.isEmpty())
    {
        return false;
    }

    qDebug() << "uploadPatientOrderAll start"
             << "url:" << uploadUrl
             << "zip:" << zipData.size() << "bytes"
             << "ct:" << ctData.size() << "bytes";

    const QByteArray boundary =
      "MedAIFormBoundary" + QUuid::createUuid().toString(QUuid::WithoutBraces).toLatin1();
    QByteArray body;
    appendTextField(body, boundary, "receiver", receiver.trimmed().toUtf8());
    appendFileField(body, boundary, "obj_zip", "model.zip", zipData);
    appendFileField(body, boundary, "ct_file", ctUploadFileName(ctFilePath), ctData);
    body += "--" + boundary + "--\r\n";

    return postByteArray(
      manager, reply, uploadUrl, boundary, body, progress,
      QObject::tr("正在上传模型和CT..."), errorMessage, nullptr);
}

bool PostManager::uploadPatientOrderModel(
    const QString& receiver,
    const QString& objZipPath,
    QProgressDialog* progress,
    QString* errorMessage,
    QString* orderIdOut)
{
    const QString uploadUrl = PATIENT_ORDER_UPLOAD_MODEL_URL;

    if (receiver.trimmed().isEmpty())
    {
        setErrorMessage(errorMessage, QObject::tr("患者姓名不能为空"));
        return false;
    }
    if (!validateZipFile(objZipPath, errorMessage))
    {
        return false;
    }

    const QByteArray zipData = readFileBytes(
      objZipPath, errorMessage, QObject::tr("无法读取模型压缩包"));
    if (zipData.isEmpty())
    {
        return false;
    }

    qDebug() << "uploadPatientOrderModel start"
             << "url:" << uploadUrl
             << "zip:" << zipData.size() << "bytes";

    const QByteArray boundary =
      "MedAIFormBoundary" + QUuid::createUuid().toString(QUuid::WithoutBraces).toLatin1();
    QByteArray body;
    appendTextField(body, boundary, "receiver", receiver.trimmed().toUtf8());
    appendFileField(body, boundary, "obj_zip", "model.zip", zipData);
    body += "--" + boundary + "--\r\n";

    QByteArray responseData;
    const bool success = postByteArray(
      manager, reply, uploadUrl, boundary, body, progress,
      QObject::tr("正在上传模型..."), errorMessage, &responseData);

    if (success && orderIdOut)
    {
        *orderIdOut = extractOrderIdFromResponse(responseData);
    }
    return success;
}

bool PostManager::uploadOrderCT(
    const QString& orderId,
    const QString& ctFilePath,
    QProgressDialog* progress,
    QString* errorMessage)
{
    const QString uploadUrl = ORDER_UPLOAD_CT_URL;

    if (orderId.trimmed().isEmpty())
    {
        setErrorMessage(errorMessage, QObject::tr("订单号不能为空"));
        return false;
    }
    qint64 ctSize = 0;
    if (!validateCtFile(ctFilePath, &ctSize, errorMessage))
    {
        return false;
    }

    const QByteArray ctData = readFileBytes(
      ctFilePath, errorMessage, QObject::tr("无法读取CT文件"));
    if (ctData.isEmpty())
    {
        return false;
    }

    qDebug() << "uploadOrderCT start"
             << "url:" << uploadUrl
             << "order:" << orderId
             << "ct:" << ctData.size() << "bytes";

    const QByteArray boundary =
      "MedAIFormBoundary" + QUuid::createUuid().toString(QUuid::WithoutBraces).toLatin1();
    QByteArray body;
    appendTextField(body, boundary, "order_id", orderId.trimmed().toUtf8());
    appendFileField(body, boundary, "ct_file", ctUploadFileName(ctFilePath), ctData);
    body += "--" + boundary + "--\r\n";

    return postByteArray(
      manager, reply, uploadUrl, boundary, body, progress,
      QObject::tr("正在上传CT..."), errorMessage, nullptr);
}
