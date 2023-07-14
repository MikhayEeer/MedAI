#include "LoginForm.h"

#include <QMessageBox>
#include <QCoreApplication>

#define CONFIGPATH QCoreApplication::applicationDirPath() + "/AppConfig.ini"

LoginForm::LoginForm(QWidget* parent): QDialog(parent)
{
    initUI();
    // load the user name in local cache
    ReadIniFile();
    connect(loginBtn,&QPushButton::clicked,this,&LoginForm::login);
    connect(signUpBtn,&QPushButton::clicked,this,&LoginForm::gotoSignUpForm);
    connect(exitBtn,&QPushButton::clicked,this,&LoginForm::quit);

    _postManager = new PostManager();
    connect(_postManager, SIGNAL(postEnded(QJsonObject)), this, SLOT(finishedLogin(QJsonObject)));

    this->setAttribute(Qt::WA_DeleteOnClose);
}

LoginForm::~LoginForm() { }


void LoginForm::login(){
    if( userNameLEd->text().length() == 0 || pwdLEd->text().length() == 0 ){
        QMessageBox::information(this, tr("Hint"), tr("Some content is empty, please fill in all the content"), QMessageBox::Yes);
        return;
    }
    if( pwdLEd->text().length() < 6){
        QMessageBox::information(this, tr("Hint"), tr("The length of the password cannot be less than 6 charcters"), QMessageBox::Yes);
        return;
    }

    loginBtn->setText(tr("Please wait"));
    loginBtn->setDisabled(true);
    signUpBtn->setDisabled(true);

    QByteArray str = QCryptographicHash::hash( (pwdLEd->text().trimmed()).toLatin1(), QCryptographicHash::Md5);
    QString MD5;
    MD5.append(str.toHex());
    // Json data
    QJsonObject json;
    json.insert("name", userNameLEd->text().trimmed());
    json.insert("password", MD5);

    _postManager->doPost(json, "/login");
}

void LoginForm::finishedLogin(QJsonObject m_res){
    if( m_res.value("state") == "Success"){
        // record info
        userInfoPhone = m_res.value("phone").toString();
        userInfoEmail = m_res.value("email").toString();
        userInfoName = m_res.value("uName").toString();
        userInfoBalance = m_res.value("balance").toString().toInt();

        if( userInfoBalance <= 0 ){
            int flag = QMessageBox::information(this, 
                            tr("Hint"), 
                            tr("Your account balance is zero \n 
                                Do you want to top up?"), 
                            QMessageBox::Yes, QMessageBox::No);
            if( flag == QMessageBox::Yes ){
                RechargeForm * tmpForm = new RechargeForm();
                // lock the window
                tmpForm->setWindowModality(Qt::ApplicationModal);
                tmpForm->show();
            }
            else exit(-1);
        }
        // have amount
        else{
            WriteIniFile("AppUserName", userNameLEd->text() );
            this->close();
        }
    }
    else {
        QMessageBox::information(this, tr("Hint"), m_res.value("state").toString(), QMessageBox::Yes);
        if (m_res.value("state").toString() == tr("wrong password")) {
            // clear
            pwdLEd->clear();
            // 
            pwdLEd->setFocus();
        }
        else userNameLEd->setFocus();

    }

    loginBtn->setText(tr("Log in"));
    loginBtn->setDisabled(false);
    signUpBtn->setDisabled(false);
}

void LoginForm::gotoSignUpForm(){
    SignUpForm * tmpForm = new SignUpForm();
    // 
    tmpForm->setWindowModality(Qt::ApplicationModal);
    tmpForm->show();
}

// 
void LoginForm::quit(){
    exit(-1);
}

//
void LoginForm::ReadIniFile(){
//        m_userNameList.clear();
    QSettings *_config = new QSettings(CONFIGPATH, QSettings::IniFormat);
    userNameLEd->setText(_config->value("AppUserName").toString());
    if(userNameLEd->text().length() > 1) pwdLEd->setFocus();
    delete _config;
}

//
void LoginForm::WriteIniFile(QString key, QString value){
    //
    QSettings *config = new QSettings(CONFIGPATH, QSettings::IniFormat);
    QVariant variant;
    variant.setValue(value);
    config->setValue(key, variant);
    delete config;
}

void LoginForm::initUI()
{
    //
    this->setWindowTitle(tr("Login Form"));

    //
    userNameLbl = new QLabel(this);   //new
    userNameLbl->setText(tr("ID:"));  //
    //
    userNameLEd = new QLineEdit(this);
    userNameLEd->setPlaceholderText(tr("Please enter your phone number or email"));

    //
    pwdLbl = new QLabel(this);
    pwdLbl->setText(tr("password:"));
    //
    pwdLEd = new QLineEdit(this);
    pwdLEd->setPlaceholderText(tr("Please enter your password"));
    pwdLEd->setEchoMode(QLineEdit::Password);//


    loginBtn = new QPushButton(this);
    loginBtn->setText(tr("Log in"));

    signUpBtn = new QPushButton(this);
    signUpBtn->setText(tr("Sign up"));

    exitBtn = new QPushButton(this);
    exitBtn->setText(tr("Exit"));

    this->setFixedSize(340,186);

    setWindowFlag(Qt::WindowCloseButtonHint, false);

    setWindowFlag(Qt::WindowContextHelpButtonHint, false);

    QHBoxLayout *HLayout1 = new QHBoxLayout;
    HLayout1->addStretch(1);
    HLayout1->addWidget(userNameLbl,1);
    HLayout1->addWidget(userNameLEd,5);
//        HLayout1->addWidget(m_userNameComboBox,5);
    HLayout1->addStretch(1);

    QHBoxLayout *HLayout2 = new QHBoxLayout;
    HLayout2->addStretch(1);
    HLayout2->addWidget(pwdLbl,1);
    HLayout2->addWidget(pwdLEd,5);
    HLayout2->addStretch(1);

    QHBoxLayout *HLayout3 = new QHBoxLayout;
    HLayout3->addStretch(1);
    HLayout3->addWidget(loginBtn,1);
    HLayout3->addWidget(signUpBtn,1);
    HLayout3->addWidget(exitBtn,1);
    HLayout3->addStretch(1);

    QVBoxLayout *VLayout = new QVBoxLayout(this);
    VLayout->addLayout(HLayout1);
    VLayout->addLayout(HLayout2);
    VLayout->addLayout(HLayout3);
    this->setLayout(VLayout);
}
