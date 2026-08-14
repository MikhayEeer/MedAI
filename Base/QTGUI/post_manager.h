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

#include "qSlicerBaseQTGUIExport.h"

class Q_SLICER_BASE_QTGUI_EXPORT PostManager : public QWidget
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
    /// 仅创建患者+订单并上传模型 zip，成功时 orderIdOut 返回订单号
    bool uploadPatientOrderModel(
      const QString& receiver,
      const QString& objZipPath,
      QProgressDialog* progress = nullptr,
      QString* errorMessage = nullptr,
      QString* orderIdOut = nullptr);
    /// 按订单号上传 CT (.nii.gz)
    bool uploadOrderCT(
      const QString& orderId,
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
