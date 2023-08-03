#include "signUpForm.h"
#include <QMessageBox>
#include <QCoreApplication>


SignUpForm::SignUpForm(QDialog *parent): QDialog(parent)
    {
        initUI();
        connect(signUpBtn,&QPushButton::clicked,this,&SignUpForm::signUp);
        connect(returnBtn,&QPushButton::clicked,this,&SignUpForm::close);
        connect(sendCaptchaBtn,&QPushButton::clicked,this,&SignUpForm::on_sendCaptchaBtn_clicked);
        cpatchaTimer = new QTimer(this);

        prePhone = "";
        preEmail = "";


        cpatchaTimer->setInterval(1000);
        connect(cpatchaTimer, SIGNAL(timeout()), this, SLOT(handleTimeout()));
        manager = new QNetworkAccessManager(this);
    }

    SignUpForm::~SignUpForm(){ }

    void SignUpForm::returnLogin(){

        delete this;
    }


    bool SignUpForm::checkFormInfo(){
        if( phoneLEd->text().length() == 0 || 
            emailLEd->text().length() == 0 || 
            userNameLEd->text().length() == 0 || 
            pwdLEd->text().length() == 0 || 
            pwd2LEd->text().length() == 0){
                
            QMessageBox::information(this, tr("Hint"), tr("Some content is empty, please check whether it has been filled!"), QMessageBox::Yes);
            return 0;
        }
        if( pwdLEd->text().length() < 6){
            QMessageBox::information(this, tr("Hint"), tr("The length of the password cannot be less than 6 characters"), QMessageBox::Yes);
            return 0;
        }

        if( pwdLEd->text() != pwd2LEd->text() ){
            QMessageBox::information(this, tr("Hint"), tr("The two passwords are not the same"), QMessageBox::Yes);
            return 0;
        }
        if( userNameLEd->text().length() > 8) {
            qDebug() << userNameLEd->text().length();
            QMessageBox::information(this, tr("Hint"), tr("The length of the user name cannot exceed 8 characters"), QMessageBox::Yes);
            return 0;
        }
        return true;
    }

    void SignUpForm::signUp(){
        if ( !checkFormInfo() ) return;
        if( captchaLEd->text().length() == 0) {
            QMessageBox::information(this, tr("Hint"), tr("Please enter the verification code"), QMessageBox::Yes);
            return ;
        }
        if( prePhone != "" && (prePhone != phoneLEd->text().trimmed() || preEmail != emailLEd->text().trimmed()) ){
            QMessageBox::information(this, tr("Hint"), tr("Phone number/email has been modified,please obtain the verification code again"), QMessageBox::Yes);
            return ;
        }
        QByteArray str = QCryptographicHash::hash((pwdLEd->text()).toLatin1(),QCryptographicHash::Md5);
        QString MD5;
        MD5.append(str.toHex());

        QJsonObject json;
        json.insert("phone", phoneLEd->text().trimmed());
        json.insert("email", emailLEd->text().trimmed());
        json.insert("name", userNameLEd->text().trimmed());
        json.insert("password", MD5);
        json.insert("captcha", captchaLEd->text().trimmed());
        QJsonDocument document;
        document.setObject(json);
        QByteArray dataArray = document.toJson(QJsonDocument::Compact);

        QNetworkRequest request;
        request.setUrl(QUrl(SERVER_URL + "/signUp"));
        request.setHeader(QNetworkRequest::ContentTypeHeader, QVariant("application/json"));

        reply = manager->post(request, dataArray);
        QEventLoop eventLoop;
        connect(manager,SIGNAL(finished(QNetworkReply*)),&eventLoop,SLOT(quit()));

        connect(reply,&QNetworkReply::finished,this,&SignUpForm::finishedSignUp);
        eventLoop.exec();
    }

    void SignUpForm::finishedSignUp(){
        QByteArray responseData = reply->readAll();

        QJsonParseError json_error;
        QJsonDocument doucment = QJsonDocument::fromJson(responseData, &json_error);
        const QJsonObject obj = doucment.object();
        if( obj.value("state") == "Success"){

            QMessageBox::information(this, tr("Hint"), tr("Registration success!"), QMessageBox::Yes);

            delete this;
        }
        else {
            QMessageBox::information(this, tr("Hint"), obj.value("state").toString(), QMessageBox::Yes);
        }
    }


    void SignUpForm::on_sendCaptchaBtn_clicked(){
        if ( !checkFormInfo() ) return;

        QJsonObject json;
        json.insert("phone", phoneLEd->text().trimmed());
        json.insert("email", emailLEd->text().trimmed());
        QJsonDocument document;
        document.setObject(json);
        QByteArray dataArray = document.toJson(QJsonDocument::Compact);

        QNetworkRequest request;
        request.setUrl(QUrl(SERVER_URL + "/sendCaptcha"));
        request.setHeader(QNetworkRequest::ContentTypeHeader, QVariant("application/json"));

        reply = manager->post(request, dataArray);
        QEventLoop eventLoop;
        connect(manager,SIGNAL(finished(QNetworkReply*)),&eventLoop,SLOT(quit()));

        connect(reply,&QNetworkReply::finished,this,&SignUpForm::afterServerSendCaptcha);
        eventLoop.exec();
    }


    void SignUpForm::afterServerSendCaptcha(){
        QByteArray responseData = reply->readAll();

        QJsonParseError json_error;
        QJsonDocument doucment = QJsonDocument::fromJson(responseData, &json_error);
        const QJsonObject obj = doucment.object();

        if( obj.value("state") == "Success"){

            limitTime = 60;

            sendCaptchaBtn->setEnabled(false);
            cpatchaTimer->start();

            QString _time = tr("(%1s)").arg(QString::number(limitTime));
            sendCaptchaBtn->setText(_time);

            prePhone = phoneLEd->text().trimmed();
            preEmail = emailLEd->text().trimmed();
            QMessageBox::information(this, tr("Hint"), tr("The verification code has been sent, please pay attention to check"), QMessageBox::Yes);
        }
        else {
            QMessageBox::information(this, tr("Hint"), obj.value("state").toString(), QMessageBox::Yes);
        }
    }


    void SignUpForm::handleTimeout(){

        limitTime -= 1;
        if (limitTime <= 0){
            cpatchaTimer->stop();

            sendCaptchaBtn->setText(tr("Send the verification code"));

            sendCaptchaBtn->setEnabled(true);
            return;
        }

        sendCaptchaBtn->setText(tr("(%1s)").arg(QString::number(limitTime)));
    }

    void SignUpForm::initUI(){

        

        /*this->setWindowTitle(tr("Registration Form"));
        phoneLbl = new QLabel(this);
        phoneLbl->setText(tr("Phone Number:"));

        phoneLEd = new QLineEdit(this);
        phoneLEd->setPlaceholderText(tr("Please enter phone number"));
        phoneLEd->setMaxLength(11);


        emailLbl = new QLabel(this);
        emailLbl->setText(tr("Email Address:"));  //

        emailLEd = new QLineEdit(this);
        emailLEd->setPlaceholderText(tr("Please enter email"));


        userNameLbl = new QLabel(this);
        userNameLbl->setText(tr("User Name:"));  //

        userNameLEd = new QLineEdit(this);
        userNameLEd->setPlaceholderText(tr("Please enter user name"));//


        pwdLbl = new QLabel(this);
        pwdLbl->setText(tr("User Password:"));

        pwdLEd = new QLineEdit(this);
        pwdLEd->setPlaceholderText(tr("Please enter your password"));
        pwdLEd->setEchoMode(QLineEdit::Password);//

        
        pwd2Lbl = new QLabel(this);
        pwd2Lbl->setText(tr("Confirm Password:"));

        pwd2LEd = new QLineEdit(this);
        pwd2LEd->setPlaceholderText(tr("Please enter the password again"));
        pwd2LEd->setEchoMode(QLineEdit::Password);//


        captchaLbl = new QLabel(this);
        captchaLbl->setText(tr("Verification Code:"));

        captchaLEd = new QLineEdit(this);
        captchaLEd->setPlaceholderText(tr("Please fill in the verification code"));
        sendCaptchaBtn = new QPushButton(this);
        sendCaptchaBtn->setText(tr("Send the verification code"));


        signUpBtn = new QPushButton(this);
        signUpBtn->setText(tr("Register"));

        returnBtn = new QPushButton(this);
        returnBtn->setText(tr("Cancel"));

        this->setFixedSize(440,285);

        setWindowFlag(Qt::WindowCloseButtonHint, false);

        setWindowFlag(Qt::WindowContextHelpButtonHint, false);

        QHBoxLayout *HLayout1 = new QHBoxLayout;
        HLayout1->addStretch(1);
        HLayout1->addWidget(phoneLbl,1);
        HLayout1->addWidget(phoneLEd,5);
        HLayout1->addStretch(1);

        QHBoxLayout *HLayout2 = new QHBoxLayout;
        HLayout2->addStretch(1);
        HLayout2->addWidget(emailLbl,1);
        HLayout2->addWidget(emailLEd,5);
        HLayout2->addStretch(1);

        QHBoxLayout *HLayout3 = new QHBoxLayout;
        HLayout3->addStretch(1);
        HLayout3->addWidget(userNameLbl,1);
        HLayout3->addWidget(userNameLEd,5);
        HLayout3->addStretch(1);

        QHBoxLayout *HLayout4 = new QHBoxLayout;
        HLayout4->addStretch(1);
        HLayout4->addWidget(pwdLbl,1);
        HLayout4->addWidget(pwdLEd,5);
        HLayout4->addStretch(1);

        QHBoxLayout *HLayout5 = new QHBoxLayout;
        HLayout5->addStretch(1);
        HLayout5->addWidget(pwd2Lbl,1);
        HLayout5->addWidget(pwd2LEd,5);
        HLayout5->addStretch(1);

        QHBoxLayout *HLayout6 = new QHBoxLayout;
        HLayout6->addStretch(1);
        HLayout6->addWidget(captchaLbl,1);
        HLayout6->addWidget(captchaLEd,3);
        HLayout6->addWidget(sendCaptchaBtn,2);
        HLayout6->addStretch(1);

        QHBoxLayout *HLayout7 = new QHBoxLayout;
        HLayout7->addStretch(1);
        HLayout7->addWidget(signUpBtn,1);
        HLayout7->addWidget(returnBtn,1);
        HLayout7->addStretch(1);

        QVBoxLayout *VLayout = new QVBoxLayout(this);
        VLayout->addLayout(HLayout1);
        VLayout->addLayout(HLayout2);
        VLayout->addLayout(HLayout3);
        VLayout->addLayout(HLayout4);
        VLayout->addLayout(HLayout5);
        VLayout->addLayout(HLayout6);
        VLayout->addLayout(HLayout7);
        this->setLayout(VLayout);*/
        setWindowFlags(Qt::Dialog | Qt::FramelessWindowHint);
        setWindowFlag(Qt::WindowCloseButtonHint, false);
        setWindowFlag(Qt::WindowContextHelpButtonHint, false);

        this->setupUi(this);
    }
