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
    QJsonDocument doucment = QJsonDocument::fromJson(responseData, &json_error);
//    emit progressDialogClosed();
//    m_progress->setHidden(true);
//    m_progress->setValue(100);
    const QJsonObject obj = doucment.object();
    emit postEnded( obj );
}


//void PostManager::cancelProgress() {
//    m_isCancel = true;
//    emit progressDialogClosed();
//}
