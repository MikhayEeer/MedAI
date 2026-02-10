#include "post_manager.h"
#include "UserInfo.h"

#include <QMessageBox>

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
    QJsonDocument document = QJsonDocument::fromJson(responseData, &json_error);

    QJsonObject obj;
    if (reply->error() != QNetworkReply::NoError) {
        obj.insert("state", reply->errorString());
    } else if (json_error.error != QJsonParseError::NoError || !document.isObject()) {
        obj.insert("state", "Network error: invalid server response");
    } else {
        obj = document.object();
    }
//    emit progressDialogClosed();
//    m_progress->setHidden(true);
//    m_progress->setValue(100);
    emit postEnded(obj);
}


//void PostManager::cancelProgress() {
//    m_isCancel = true;
//    emit progressDialogClosed();
//}
