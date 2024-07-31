#include "passworddialog.h"

PasswordDialog::PasswordDialog(QWidget *parent) : QDialog(parent) {
    setWindowTitle("请输入管理员特殊密码");
    // 不显示右上角的帮助
    setWindowFlag(Qt::WindowContextHelpButtonHint, false);
    this->setFixedSize(420,200);

    passwordLabel = new QLabel("特殊密码:", this);
    passwordLineEdit = new QLineEdit(this);
    passwordLineEdit->setEchoMode(QLineEdit::Password);

    confirmButton = new QPushButton("确认", this);
    returnButton = new QPushButton("返回", this);

    connect(confirmButton, &QPushButton::clicked, this, &PasswordDialog::onConfirmClicked);
    connect(returnButton, &QPushButton::clicked, this, &PasswordDialog::onReturnClicked);

    QVBoxLayout *layout = new QVBoxLayout(this);
    layout->addWidget(passwordLabel);
    layout->addWidget(passwordLineEdit);
    layout->addWidget(confirmButton);
    layout->addWidget(returnButton);


    _postManager = new PostManager();
    connect(_postManager, SIGNAL(postEnded(QJsonObject)), this, SLOT(finishVerify(QJsonObject)));
}

void PasswordDialog::onConfirmClicked() {
    QJsonObject json;
    json.insert("vcode", passwordLineEdit->text().trimmed());

    _postManager->doPost(json, "/admin_verify");
}

void PasswordDialog::onReturnClicked() {
    this->close();
}

void PasswordDialog::finishVerify(QJsonObject m_res){
    if( m_res.value("state") == "ok"){
        this->hide();
        UserListWidget * tmpForm = new UserListWidget();
        tmpForm->setWindowModality(Qt::ApplicationModal);
        tmpForm->show();
    }
    else{
        QMessageBox::information(this, "提示", "特殊密码输入错误\n（如果您是管理员，请联系软件工程师）", QMessageBox::Yes);
    }
}
