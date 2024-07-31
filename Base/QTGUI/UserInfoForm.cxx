#include "UserInfoForm.h"
#include "RechargeForm.h"
#include <QMessageBox>
#include <QCoreApplication>


UserInfoForm::UserInfoForm(QDialog *parent):
    QDialog(parent)
{
    initUI();
    connect(rechargeBtn,&QPushButton::clicked,this,&UserInfoForm::gotoRechargeForm);
    connect(getBalanceDetailsBtn,&QPushButton::clicked,this,&UserInfoForm::getBalanceDetails);
    connect(returnBtn,&QPushButton::clicked,this,&UserInfoForm::close);

    _postManager = new PostManager();
    connect(_postManager, SIGNAL(postEnded(QJsonObject)), this, SLOT(afterGetDetails(QJsonObject)));

    tableView = nullptr;
    model = nullptr;

    this->setAttribute(Qt::WA_DeleteOnClose);
}

UserInfoForm::~UserInfoForm(){
    if (tableView != nullptr) delete tableView;
    if (model != nullptr) delete model;
}

void UserInfoForm::getBalanceDetails(){
    QJsonObject json;
    json.insert("phone", phoneLEd->text().trimmed());

    _postManager->doPost(json, "/getBalanceDetails");
}

void UserInfoForm::afterGetDetails(QJsonObject obj){
    if( obj.value("state") != "Success"){
        QMessageBox::information(this, tr("Hint"), tr("Server error, please try again"), QMessageBox::Yes);
        return;
    }

    tableView = new QTableView;
    tableView->resize(630, 420);

    model = new QStandardItemModel();
    
    model->setHorizontalHeaderLabels({ tr("Name") , tr("Amount of change"), tr("Time") });

    tableView->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);

    int len = obj.value("len").toString().toInt();
    for (int _row = 0; _row < len; _row++) {

        model->setItem(_row, 0, new QStandardItem(obj.value("data")[_row]["note"].toString()));

        int _data = obj.value("data")[_row]["amount"].toInt();
        model->setItem(_row, 1, new QStandardItem(QString::number(_data)));

        _data = obj.value("data")[_row]["stamp"].toInt();
        QDateTime time = QDateTime::fromSecsSinceEpoch(_data);
        QString strStartTime = time.toString("yyyy-MM-dd hh:mm:ss");
        model->setItem(_row, 2, new QStandardItem(strStartTime));

        model->item(_row, 0)->setTextAlignment(Qt::AlignCenter);
        model->item(_row, 1)->setTextAlignment(Qt::AlignCenter);
        model->item(_row, 2)->setTextAlignment(Qt::AlignCenter);
    }
    if( len >= 299 ){
        QMessageBox::information(this, tr("Hint"), 
            tr("Users can query the most recent 300 records \n \
                if you need all the data. please contact the database administrator"), 
            QMessageBox::Yes);
    }

    tableView->setModel(model);
    tableView->setWindowModality(Qt::ApplicationModal);
    tableView->show();
}


void UserInfoForm::receiveChangesInBalance(QString str){
    userInfoBalance = str.toInt();
    balanceLEd->setText(str);
}


void UserInfoForm::gotoRechargeForm(){
    RechargeForm * tmpForm = new RechargeForm();

    connect(tmpForm, SIGNAL(sendText(QString)), this, SLOT(receiveChangesInBalance(QString)));

    tmpForm->setWindowModality(Qt::ApplicationModal);
    tmpForm->show();
}

void UserInfoForm::initUI(){
    this->setWindowTitle(tr("Account info"));

    //
    phoneLbl = new QLabel(this);   //new
    phoneLbl->setText(tr("Phone Number:"));  //
    phoneLEd = new QLineEdit(this);
    phoneLEd->setText(userInfoPhone);
    //phoneLEd->setReadOnly(true);
    phoneLEd->setDisabled(true);

    //
    emailLbl = new QLabel(this);   //new
    emailLbl->setText(tr("User Email:"));  //
    emailLEd = new QLineEdit(this);
    emailLEd->setText(userInfoEmail);
    //emailLEd->setReadOnly(true);
    emailLEd->setDisabled(true);


    userNameLbl = new QLabel(this);   //
    userNameLbl->setText(tr("User Name:"));  //
    userNameLEd = new QLineEdit(this);
    userNameLEd->setText(userInfoName);
    userNameLEd->setDisabled(true);


    balanceLbl = new QLabel(this);
    balanceLbl->setText(tr("Account Balance:"));
    balanceLEd = new QLineEdit(this);
    balanceLEd->setText(QString::number(userInfoBalance));
    balanceLEd->setDisabled(true);


    rechargeBtn = new QPushButton(this);
    rechargeBtn->setText(tr("Balance Recharge"));
    getBalanceDetailsBtn = new QPushButton(this);
    getBalanceDetailsBtn->setText(tr("View Bill"));
    returnBtn = new QPushButton(this);
    returnBtn->setText(tr("Return"));

    this->setFixedSize(460,220);

    setWindowFlag(Qt::WindowCloseButtonHint, false);

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
    HLayout4->addWidget(balanceLbl,1);
    HLayout4->addWidget(balanceLEd,5);
    HLayout4->addStretch(1);

    QHBoxLayout *HLayout5 = new QHBoxLayout;
    HLayout5->addStretch(3);
    HLayout5->addWidget(rechargeBtn,2);
    HLayout5->addWidget(getBalanceDetailsBtn,2);
    HLayout5->addWidget(returnBtn,2);
    HLayout5->addStretch(3);

    QVBoxLayout *VLayout = new QVBoxLayout(this);
    VLayout->addLayout(HLayout1);
    VLayout->addLayout(HLayout2);
    VLayout->addLayout(HLayout3);
    VLayout->addLayout(HLayout4);
    VLayout->addLayout(HLayout5);
    this->setLayout(VLayout);


    setWindowFlag(Qt::WindowCloseButtonHint, false);

    setWindowFlag(Qt::WindowContextHelpButtonHint, false);
}
