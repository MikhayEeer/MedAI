#ifndef USERINFOFORM_H
#define USERINFOFORM_H

#pragma execution_character_set("utf-8")
#include "UserInfo.h"
#include "post_manager.h"
#include "qSlicerBaseQTGUIExport.h"

#include <QLabel>
#include <QDialog>
#include <QString>
#include <QLineEdit>
#include <QPushButton>
#include <QHBoxLayout>
#include <QVBoxLayout>

#include<QJsonObject>
#include<QJsonDocument>


#include <QTableView>
#include <QHeaderView>
#include <QStandardItemModel>

#pragma execution_character_set("utf-8")

class Q_SLICER_BASE_QTGUI_EXPORT UserInfoForm : public QDialog
{
    Q_OBJECT //
public:
    explicit UserInfoForm(QDialog *parent = nullptr);  //explicit 
    ~UserInfoForm();
    void initUI();
    void gotoRechargeForm();
    void getBalanceDetails();

public slots:
    void afterGetDetails(QJsonObject);
    void receiveChangesInBalance(QString str);

private:
    QLabel *phoneLbl;            // 
    QLabel *emailLbl;            // 
    QLabel *userNameLbl;         // 
    QLabel *balanceLbl;          // 
    QLineEdit *phoneLEd;         // 
    QLineEdit *emailLEd;         // 
    QLineEdit *userNameLEd;      // 
    QLineEdit *balanceLEd;       // 
    QPushButton *rechargeBtn;    // 
    QPushButton *getBalanceDetailsBtn;      // 
    QPushButton *returnBtn;      //


    QTableView *tableView;      // 
    QStandardItemModel* model;
    PostManager* _postManager;
};

#endif // USERINFOFORM_H
