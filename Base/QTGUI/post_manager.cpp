#include "post_manager.h"
#include "UserInfo.h"

#include <QMessageBox>
#include <QUuid>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QNetworkAccessManager>
#include <QUrl>
#include <QDebug>

namespace
{
QByteArray buildPatientOrderUploadBody(
    const QString& boundary,
    const QString& receiver,
    const QString& objZipPath,
    const QByteArray& zipData,
    const QString& ctFilePath,
    const QByteArray& ctData)
{
  QByteArray body;

  auto appendField = [&body, &boundary](const QString& name, const QByteArray& value) {
    body += "--";
    body += boundary.toUtf8();
    body += "\r\n";
    body += "Content-Disposition: form-data; name=\"";
    body += name.toUtf8();
    body += "\"\r\n\r\n";
    body += value;
    body += "\r\n";
  };

  auto appendFile = [&body, &boundary](const QString& name, const QString& fileName, const QByteArray& data) {
    body += "--";
    body += boundary.toUtf8();
    body += "\r\n";
    body += "Content-Disposition: form-data; name=\"";
    body += name.toUtf8();
    body += "\"; filename=\"";
    body += fileName.toUtf8();
    body += "\"\r\n";
    body += "Content-Type: application/octet-stream\r\n\r\n";
    body += data;
    body += "\r\n";
  };

  appendField("receiver", receiver.toUtf8());
  appendFile("obj_zip", QFileInfo(objZipPath).fileName(), zipData);
  appendFile("ct_file", QFileInfo(ctFilePath).fileName(), ctData);
  body += "--";
  body += boundary.toUtf8();
  body += "--\r\n";
  return body;
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

    //if (m_isCancel) return; // *new QJsonObject

    QByteArray responseData = reply->readAll();

    QJsonParseError json_error;
    QJsonDocument doucment = QJsonDocument::fromJson(responseData, &json_error);
//    emit progressDialogClosed();
//    m_progress->setHidden(true);
//    m_progress->setValue(100);
    const QJsonObject obj = doucment.object();
    emit postEnded( obj );
}

bool PostManager::uploadPatientOrderAll(
    const QString& receiver,
    const QString& objZipPath,
    const QString& ctFilePath,
    QProgressDialog* progress)
{
    const QString uploadUrl = PATIENT_ORDER_UPLOAD_URL;
    qDebug() << "uploadPatientOrderAll start, url:" << uploadUrl;

    QFile zipFile(objZipPath);
    if (!zipFile.open(QIODevice::ReadOnly))
    {
        qWarning() << "uploadPatientOrderAll: cannot open zip file" << objZipPath;
        return false;
    }
    const QByteArray zipData = zipFile.readAll();
    zipFile.close();

    QFile ctFileReader(ctFilePath);
    if (!ctFileReader.open(QIODevice::ReadOnly))
    {
        qWarning() << "uploadPatientOrderAll: cannot open ct file" << ctFilePath;
        return false;
    }
    const QByteArray ctData = ctFileReader.readAll();
    ctFileReader.close();

    if (progress)
    {
        progress->setLabelText(QObject::tr("正在上传模型和CT..."));
        progress->setValue(70);
        QApplication::processEvents();
    }

    const QString boundary = "MedAIFormBoundary" + QUuid::createUuid().toString(QUuid::WithoutBraces);
    const QByteArray uploadBody = buildPatientOrderUploadBody(
      boundary, receiver, objZipPath, zipData, ctFilePath, ctData);

    QNetworkRequest networkRequest;
    networkRequest.setUrl(QUrl(uploadUrl));
    networkRequest.setHeader(
      QNetworkRequest::ContentTypeHeader,
      QVariant(QString("multipart/form-data; boundary=%1").arg(boundary)));

    QNetworkReply* uploadReply = manager->post(networkRequest, uploadBody);

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
    timeoutTimer.start();
    eventLoop.exec();

    const bool timedOut = !uploadReply->isFinished();
    if (timedOut)
    {
        qWarning() << "uploadPatientOrderAll: request timed out";
        uploadReply->abort();
    }

    const bool success = !timedOut && uploadReply->error() == QNetworkReply::NoError;
    const QByteArray responseData = uploadReply->readAll();
    if (success)
    {
        qDebug() << "uploadPatientOrderAll success:" << responseData;
    }
    else
    {
        qWarning() << "uploadPatientOrderAll failed:" << uploadReply->errorString();
        qWarning() << responseData;
    }

    if (progress)
    {
        progress->setValue(success ? 100 : progress->value());
        QApplication::processEvents();
    }

    uploadReply->deleteLater();
    return success;
}


//void PostManager::cancelProgress() {
//    m_isCancel = true;
//    emit progressDialogClosed();
//}
