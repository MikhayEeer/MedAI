#ifndef SIGNUPFORM_H
#define SIGNUPFORM_H

#pragma execution_character_set("utf-8")
#include "qSlicerBaseQTGUIExport.h"
#include "ui_qSlicerSignUpForm.h"

#include <QDialog>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QtDebug>
#include <QHBoxLayout>
#include <QVBoxLayout>
//md5
#include <QCryptographicHash>
//
#include <QtNetwork>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
// json
#include<QJsonObject>
#include<QJsonDocument>

#include "UserInfo.h"


class Q_SLICER_BASE_QTGUI_EXPORT SignUpForm 
    : public QDialog
    , public Ui_SignUpForm
{
    Q_OBJECT //
public:
    explicit SignUpForm(QDialog *parent = nullptr);  //explicit 
    ~SignUpForm();
    void initUI();

public slots:
    void signUp(); //sign up
    void finishedSignUp();
    // 
    bool checkFormInfo();
    void returnLogin();
    void handleTimeout();
    void on_sendCaptchaBtn_clicked();
    void afterServerSendCaptcha();

private:
    /*
    QLabel *phoneLbl;            // 
    QLabel *emailLbl;            // 
    QLabel *userNameLbl;         // 
    QLabel *pwdLbl;              // 
    QLabel *pwd2Lbl;             // 
    QLabel *captchaLbl;          // 

    QLineEdit *phoneLEd;         // 
    QLineEdit *emailLEd;         // 
    QLineEdit *userNameLEd;      // 
    QLineEdit *pwdLEd;           // 
    QLineEdit *pwd2LEd;          // 
    QLineEdit *captchaLEd;       // 

    QPushButton *signUpBtn;      // 
    QPushButton *returnBtn;      // 
    QPushButton *sendCaptchaBtn; // 
*/
    QTimer *cpatchaTimer;        // 
    int limitTime;

    // 
    QString prePhone;       // 
    QString preEmail;       // 

    QUrl url;
    QNetworkRequest req;
    QNetworkReply *reply;
    QNetworkAccessManager *manager;

};
#endif // SIGNUPFORM_H
