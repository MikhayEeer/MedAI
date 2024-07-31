#ifndef RECHARGEFORM_H
#define RECHARGEFORM_H

#pragma execution_character_set("utf-8")
#include <QDialog>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QtDebug>
//md5
#include <QCryptographicHash>
#include <QtNetwork>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
//JSON
#include<QJsonObject>
#include<QJsonDocument>
//
#include "UserInfo.h"


class RechargeForm : public QDialog
{
    Q_OBJECT //
public:
    explicit RechargeForm(QDialog *parent = nullptr);  //explicit 
    ~RechargeForm();
    void initUI();

signals:
    void sendText(QString str); // 

public slots:
    void recharge(); // 
    void finishedRecharge(); // 

private:
    QLabel *phoneLbl;            // 
    QLabel *emailLbl;            // 
    QLabel *userNameLbl;         //
    QLabel *amountLbl;           // 
    QLabel *balanceLbl;          //
    //QLineEdit *phoneLEd;         // 
    QLineEdit *emailLEd;         // 
    QLineEdit *userNameLEd;      //
    QLineEdit *amountLEd;        // 
    QPushButton *okBtn;          //
    QPushButton *exitBtn;        //

    QUrl url;
    QNetworkRequest req;
    QNetworkReply *reply;
    QNetworkAccessManager *manager;

};
#endif // RECHARGEFORM_H
