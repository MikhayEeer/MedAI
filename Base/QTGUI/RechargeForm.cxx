#include "LoginForm.h"
#include "RechargeForm.h"
#include <QMessageBox>
#include <QCoreApplication>


RechargeForm::RechargeForm(QDialog *parent):
    QDialog(parent)
    {
        initUI();

        connect(okBtn,&QPushButton::clicked,this,&RechargeForm::recharge);
        connect(exitBtn,&QPushButton::clicked,this,&RechargeForm::close);
        manager = new QNetworkAccessManager(this);
    }

    RechargeForm::~RechargeForm() {}

    void RechargeForm::recharge(){

        QJsonObject json;
        json.insert("phone", userInfoPhone);

        json.insert("amount", amountLEd->text());

        QJsonDocument document;
        document.setObject(json);
        QByteArray dataArray = document.toJson(QJsonDocument::Compact);

        QNetworkRequest request;
        request.setUrl(QUrl(SERVER_URL + "/recharge"));
        request.setHeader(QNetworkRequest::ContentTypeHeader, QVariant("application/json"));

        reply = manager->post(request, dataArray);
        QEventLoop eventLoop;
        connect(manager,SIGNAL(finished(QNetworkReply*)),&eventLoop,SLOT(quit()));
        connect(reply,&QNetworkReply::finished,this,&RechargeForm::finishedRecharge);
        eventLoop.exec();
    }

    void RechargeForm::finishedRecharge(){
        QByteArray responseData = reply->readAll();
        QJsonParseError json_error;
        QJsonDocument doucment = QJsonDocument::fromJson(responseData, &json_error);
        const QJsonObject obj = doucment.object();

        if( obj.value("state") == "Success"){
            userInfoBalance += amountLEd->text().toInt();

            emit sendText(QString::number(userInfoBalance));
            QMessageBox* msgBox = new QMessageBox(QMessageBox::Question, tr("Hint"), tr("Recharge successfully"), QMessageBox::Yes);
            msgBox->button(QMessageBox::Yes)->setText(tr("OK"));
            msgBox->setWindowFlag(Qt::WindowCloseButtonHint, false);
            int flag = msgBox->exec();
            if (flag == QMessageBox::Yes) {
                close();
            }
        }
        else {
            QMessageBox::information(this, tr("Hint"), obj.value("state").toString(), QMessageBox::Yes);
        }
    }

    void RechargeForm::initUI()
    {

        this->setWindowTitle(tr("Recharge Form"));


        amountLbl = new QLabel(this);
        amountLbl->setText(tr("Recharge amount:"));
        amountLEd = new QLineEdit(this);
        amountLEd->setPlaceholderText(tr("Please enter the amount you want to recharge"));


        okBtn = new QPushButton(this);
        okBtn->setText(tr("OK"));

        exitBtn = new QPushButton(this);
        exitBtn->setText(tr("Exit"));

        this->setFixedSize(360,240);


        setWindowFlag(Qt::WindowCloseButtonHint, false);

        QHBoxLayout *HLayout1 = new QHBoxLayout;
        HLayout1->addStretch(1);
        HLayout1->addWidget(amountLbl,1);
        HLayout1->addWidget(amountLEd,5);
        HLayout1->addStretch(1);


        QHBoxLayout *HLayout3 = new QHBoxLayout;
        HLayout3->addStretch(1);
        HLayout3->addWidget(okBtn,2);
        HLayout3->addWidget(exitBtn,2);
        HLayout3->addStretch(1);

        QVBoxLayout *VLayout = new QVBoxLayout(this);
        VLayout->addLayout(HLayout1);
//        VLayout->addLayout(HLayout2);
        VLayout->addLayout(HLayout3);
        this->setLayout(VLayout);
    }
