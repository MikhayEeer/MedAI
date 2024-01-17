#ifndef BACKEND_AI_PROCESSING_MANAGER_H
#define BACKEND_AI_PROCESSING_MANAGER_H

#pragma execution_character_set("utf-8")
#include <QObject>
#include <QWidget>
#include <QDialog>
#include <QLabel>
#include <QLineEdit>
#include <QComboBox>
#include <QPushButton>
#include <QHBoxLayout>
#include <QVBoxLayout>
#include <QProgressDialog>
#include <QSettings>
#include <QNetworkAccessManager>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QFile>
#include <QFileDialog>
#include <QtNetwork>
#include <QHttpMultiPart>
#include <QMessageBox>
#include "qSlicerBaseQTGUIExport.h"

class Q_SLICER_BASE_QTGUI_EXPORT backendAiManager : public QWidget
{
    Q_OBJECT
public:
    explicit backendAiManager(QWidget *parent = nullptr);
    ~backendAiManager();
    void uploadFile(QStringList files);
    void showFileDialog();

private:
    QLabel      *userNameLbl;
    QLabel      *pwdLbl;
//    QPushButton *loginBtn;       //登录按钮
//    QPushButton *exitBtn;        //退出按钮
    QProgressDialog *m_progress;
    QString m_result_path;

    QHttpMultiPart *multiPart;
    QNetworkReply* reply;
    QNetworkAccessManager* manager;
    QMessageBox *finishedDialog;

    void initUI();


};

#endif // BACKEND_AI_PROCESSING_MANAGER_H
