#include "post_manager.h"
#include "UserInfo.h"

#include <QNetworkRequest>
#include <QNetworkReply>
#include <QNetworkAccessManager>
#include <QNetworkProxy>
#include <QHttpMultiPart>
#include <QHttpPart>
#include <QUrl>
#include <QDebug>
#include <QJsonArray>

namespace
{
bool isZipArchive(const QByteArray& data)
{
  return data.size() >= 4 && data.startsWith("PK\x03\x04");
}

QString ctUploadFileName(const QString& ctFilePath)
{
  QString fileName = QFileInfo(ctFilePath).fileName();
  if (!fileName.endsWith(".nii.gz", Qt::CaseInsensitive))
  {
    fileName += ".nii.gz";
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

QByteArray readFileData(const QString& filePath, QString* errorMessage, const QString& errorText)
{
  QFile file(filePath);
  if (!file.open(QIODevice::ReadOnly))
  {
    qWarning() << "readFileData: cannot open" << filePath;
    setErrorMessage(errorMessage, errorText);
    return QByteArray();
  }
  const QByteArray data = file.readAll();
  file.close();
  return data;
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
    qDebug() << "uploadPatientOrderAll start, url:" << uploadUrl;

    if (receiver.trimmed().isEmpty())
    {
        setErrorMessage(errorMessage, QObject::tr("患者姓名不能为空"));
        return false;
    }

    const QByteArray zipData = readFileData(
      objZipPath, errorMessage, QObject::tr("无法读取模型压缩包"));
    if (zipData.isEmpty())
    {
        return false;
    }
    if (!isZipArchive(zipData))
    {
        qWarning() << "uploadPatientOrderAll: invalid zip file" << objZipPath << "size:" << zipData.size();
        setErrorMessage(errorMessage, QObject::tr("模型压缩包无效，请重新导出后再试"));
        return false;
    }

    const QByteArray ctData = readFileData(
      ctFilePath, errorMessage, QObject::tr("无法读取CT文件"));
    if (ctData.isEmpty())
    {
        return false;
    }

    if (progress)
    {
        progress->setLabelText(QObject::tr("正在上传模型和CT..."));
        progress->setValue(70);
        QApplication::processEvents();
    }

    QHttpMultiPart* multiPart = new QHttpMultiPart(QHttpMultiPart::FormDataType);

    QHttpPart receiverPart;
    receiverPart.setHeader(
      QNetworkRequest::ContentDispositionHeader,
      QVariant("form-data; name=\"receiver\""));
    receiverPart.setBody(receiver.trimmed().toUtf8());
    multiPart->append(receiverPart);

    QHttpPart zipPart;
    zipPart.setHeader(
      QNetworkRequest::ContentDispositionHeader,
      QVariant("form-data; name=\"obj_zip\"; filename=\"model.zip\""));
    zipPart.setHeader(
      QNetworkRequest::ContentTypeHeader,
      QVariant("application/x-zip-compressed"));
    zipPart.setBody(zipData);
    multiPart->append(zipPart);

    const QString ctFileName = ctUploadFileName(ctFilePath);
    QHttpPart ctPart;
    ctPart.setHeader(
      QNetworkRequest::ContentDispositionHeader,
      QVariant(QString("form-data; name=\"ct_file\"; filename=\"%1\"").arg(ctFileName)));
    ctPart.setHeader(
      QNetworkRequest::ContentTypeHeader,
      QVariant("application/x-gzip"));
    ctPart.setBody(ctData);
    multiPart->append(ctPart);

    QNetworkRequest networkRequest;
    networkRequest.setUrl(QUrl(uploadUrl));

    // Bypass system proxy (Slicer enables it globally); curl typically connects directly.
    QNetworkAccessManager uploadManager;
    uploadManager.setProxy(QNetworkProxy::NoProxy);

    QNetworkReply* uploadReply = uploadManager.post(networkRequest, multiPart);
    multiPart->setParent(uploadReply);

    if (progress)
    {
        QObject::connect(uploadReply, &QNetworkReply::uploadProgress, progress,
          [progress](qint64 sent, qint64 total) {
              if (total <= 0)
              {
                  return;
              }
              const int uploadProgress = 70 + static_cast<int>((sent * 25) / total);
              progress->setValue(qMin(uploadProgress, 95));
          });
    }

    QEventLoop eventLoop;
    QTimer timeoutTimer;
    timeoutTimer.setSingleShot(true);
    timeoutTimer.setInterval(600000);
    QObject::connect(&timeoutTimer, &QTimer::timeout, &eventLoop, &QEventLoop::quit);
    QObject::connect(uploadReply, &QNetworkReply::finished, &eventLoop, &QEventLoop::quit);
    QObject::connect(uploadReply, &QNetworkReply::errorOccurred, &eventLoop, &QEventLoop::quit);
    timeoutTimer.start();
    eventLoop.exec();

    const bool timedOut = !uploadReply->isFinished();
    if (timedOut)
    {
        qWarning() << "uploadPatientOrderAll: request timed out";
        uploadReply->abort();
        setErrorMessage(errorMessage, QObject::tr("上传超时，请稍后重试"));
        uploadReply->deleteLater();
        return false;
    }

    const QByteArray responseData = uploadReply->readAll();
    const int httpStatus = uploadReply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
    const bool networkOk = uploadReply->error() == QNetworkReply::NoError;

    bool success = networkOk && httpStatus >= 200 && httpStatus < 300;
    if (success)
    {
        qDebug() << "uploadPatientOrderAll success:" << responseData;
    }
    else
    {
        const QString responseError = networkOk
          ? parseUploadErrorMessage(responseData, httpStatus)
          : uploadReply->errorString();
        qWarning() << "uploadPatientOrderAll failed:" << responseError;
        qWarning() << "HTTP status:" << httpStatus << "response:" << responseData;
        setErrorMessage(errorMessage, responseError);
    }

    if (progress)
    {
        progress->setValue(success ? 100 : progress->value());
        QApplication::processEvents();
    }

    uploadReply->deleteLater();
    return success;
}
