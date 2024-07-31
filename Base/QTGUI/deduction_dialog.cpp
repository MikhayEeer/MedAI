#include "deduction_dialog.h"
#include "UserInfo.h"
#include <QMessageBox>
#include <QCoreApplication>

DeductionDialog::DeductionDialog(int cost, QString note, QWidget *parent)
    : QDialog{parent}
{
    initUI();
    connect(m_yesBtn,&QPushButton::clicked,this,&DeductionDialog::yesBtn_clicked);
    connect(m_noBtn,&QPushButton::clicked,this,&DeductionDialog::noBtn_clicked);

    m_cost = cost;
    m_note = note;

    _postManager = new PostManager();
    connect(_postManager, SIGNAL(postEnded(QJsonObject)), this, SLOT(finishedDeduction(QJsonObject)));

    this->setAttribute(Qt::WA_DeleteOnClose);
}

void DeductionDialog::yesBtn_clicked(){
    // Json data
    QJsonObject json;
    json.insert("phone", userInfoPhone);
    json.insert("amount", QString::number(m_cost));
    json.insert("note", m_note);

    _postManager->doPost(json, "/pay");
}

void DeductionDialog::finishedDeduction(QJsonObject obj){
    if (obj.value("state") == "Success") {
        userInfoBalance = obj.value("balance").toString().toInt();
        int flag = QMessageBox::information(this, tr("Hint"),  tr("Successfully debited"), QMessageBox::Yes);
        emit deductionAccomplished();
        if( flag == QMessageBox::Yes ){
            this->close();
        }
    }
    else {
        if( obj.value("state").toString() == "")
            QMessageBox::information(NULL, tr("Hint"), tr("\nThe server is crowed, please try again!\n"), QMessageBox::Ok);
        else
            QMessageBox::information(NULL, tr("Hint"), obj.value("state").toString(), QMessageBox::Ok);
    }
}

void DeductionDialog::noBtn_clicked(){
    this->close();
}

void DeductionDialog::initUI()
{
    this->setWindowTitle(tr("Deduction Reminder"));
    m_tip = new QLabel(tr("\nDo you want to proceed ? Fees needed if you continue to operate.\n"));

    m_yesBtn = new QPushButton();
    m_yesBtn->setText(tr("Continue"));
    m_noBtn = new QPushButton();
    m_noBtn->setText(tr("Cancel"));

    this->setFixedSize(340,186);
    // 不显示右上角的关闭
    setWindowFlag(Qt::WindowCloseButtonHint, false);
    // 不显示右上角的帮助
    setWindowFlag(Qt::WindowContextHelpButtonHint, false);

    QHBoxLayout *HLayout1 = new QHBoxLayout;
    HLayout1->addStretch(1);
    HLayout1->addWidget(m_tip,5);
    HLayout1->addStretch(1);

    QHBoxLayout *HLayout2 = new QHBoxLayout;
    HLayout2->addStretch(2);
    HLayout2->addWidget(m_yesBtn,3);
    HLayout2->addWidget(m_noBtn,3);
    HLayout2->addStretch(2);

    QVBoxLayout *VLayout = new QVBoxLayout(this);
    VLayout->addLayout(HLayout1);
    VLayout->addLayout(HLayout2);
    this->setLayout(VLayout);
}
