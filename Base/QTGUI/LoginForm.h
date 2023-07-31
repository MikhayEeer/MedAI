#ifndef LOGINFORM_H
#define LOGINFORM_H

#include "UserInfo.h"
#include "signUpForm.h"
#include "RechargeForm.h"
#include "post_manager.h"
#include "qSlicerBaseQTGUIExport.h"

#include "ui_qSlicerLoginForm.h"

#include <QDialog>
#include <QLabel>
#include <QLineEdit>
#include <QComboBox>
#include <QPushButton>
#include <QHBoxLayout>
#include <QVBoxLayout>
#include <QSettings>
#include <QtCore>
#include <QtGui>
#include <QtWidgets>

//#include "Resources/qSlicerUserResources.qrc"

#include <QCryptographicHash>

#include<QJsonObject>
#include<QJsonDocument>

#pragma execution_character_set("utf-8")

class Q_SLICER_BASE_QTGUI_EXPORT LoginForm 
    : public QDialog
    , public Ui_LoginForm
{
    Q_OBJECT //
public:
    explicit LoginForm(QWidget* parent = nullptr);  //explicit 
    ~LoginForm();
    void ReadIniFile(); //
    void WriteIniFile(QString key, QString value);

public slots:
    void login(); //
    void finishedLogin(QJsonObject m_res);
    void gotoSignUpForm();
    void quit();

private:
    QLabel      *userNameLbl;
    QLabel      *pwdLbl;
    QLineEdit   *userNameLEd;      //
    QLineEdit   *pwdLEd;           //
    QPushButton *loginBtn;       //
    QPushButton *signUpBtn;      //
    QPushButton *exitBtn;        //
    void initUI();

//    QStringList m_userNameList;
    bool m_isNewUserName;

    PostManager* _postManager;
};

#endif // LOGINFORM_H
