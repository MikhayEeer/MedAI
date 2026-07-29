#ifndef POSTMANAGER_H
#define POSTMANAGER_H

#include <QWidget>

#include <QtNetwork>
#include <QNetworkReply>
#include <QProgressDialog>
#include <QNetworkRequest>
#include <QNetworkAccessManager>
#include <QJsonObject>
#include <QJsonDocument>
#include <QFile>
#include <QFileInfo>
#include <QEventLoop>
#include <QTimer>
#include <QApplication>

class PostManager : public QWidget
{
    Q_OBJECT
public:
    explicit PostManager(QWidget *parent = nullptr);
    void doPost(QJsonObject json, QString postUrl);
    bool uploadPatientOrderAll(
      const QString& receiver,
      const QString& objZipPath,
      const QString& ctFilePath,
      QProgressDialog* progress = nullptr,
      QString* errorMessage = nullptr);

signals:
    void postEnded(QJsonObject);

public slots:
//    void cancelProgress();

private:
    int m_cost;
    QString m_note;

    bool m_isCancel;

//    QProgressDialog *m_progress;
    QNetworkReply* reply;
    QNetworkAccessManager* manager;
};

#endif // POSTMANAGER_H
