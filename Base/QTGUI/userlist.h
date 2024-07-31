#ifndef USERLIST_H
#define USERLIST_H

#pragma execution_character_set("utf-8")

#include <QObject>
#include <QWidget>
#include <QTableWidget>
#include <QTableWidgetItem>
#include <QPushButton>
#include <QHBoxLayout>
#include <QVBoxLayout>
#include <QMap>
#include <QMessageBox>

#include <QJsonObject>
#include <QJsonDocument>
#include "post_manager.h"
#include "qSlicerBaseQTGUIExport.h"

class Q_SLICER_BASE_QTGUI_EXPORT UserListWidget : public QWidget {
    Q_OBJECT

public:
    UserListWidget(QWidget *parent = nullptr) : QWidget(parent) {
        // 创建表格
        tableWidget = new QTableWidget(this);
        tableWidget->setColumnCount(6); // 假设有6列：邮箱，用户名，手机号，AI使用次数，登录状态，登录按钮

        tableWidget->setRowCount(0); // 初始行数
        // 设置表头
        QStringList headers;
        headers << "邮箱" << "用户名" << "手机号" << "AI使用次数" << "是否可以登录" << "（按钮）";
        tableWidget->setHorizontalHeaderLabels(headers);

        this->setWindowTitle("User Management");
        this->setFixedSize(1200, 900);

        _postManager = new PostManager();
        connect(_postManager, SIGNAL(postEnded(QJsonObject)), this, SLOT(getDetails(QJsonObject)));

        QJsonObject json;
        _postManager->doPost(json, "/get_users_info");

        _post_login_state = new PostManager();
        connect(_post_login_state, SIGNAL(postEnded(QJsonObject)), this, SLOT(tip_login_state_changed(QJsonObject)));
    }

private slots:
    void onLoginButtonClicked(int row) {
        QPushButton *button = qobject_cast<QPushButton *>(sender());
        if (button) {
            // 从按钮的属性中获取行号
            int now_row = button->property("row").toInt();
            _click_row = now_row;
            QTableWidgetItem *emailItem = tableWidget->item(_click_row, 0);
            QTableWidgetItem *stateItem = tableWidget->item(_click_row, 4);
            QJsonObject json;
            json.insert("email", emailItem->text().trimmed());
            json.insert("can_login", stateItem->text().trimmed());
            qDebug() << emailItem->text();

            _post_login_state->doPost(json, "/update_user_can_login");
        }
    }

    void tip_login_state_changed(QJsonObject jsonObj){
        if( jsonObj.value("state") == "ok"){
            QTableWidgetItem *loginStatusItem = tableWidget->item(_click_row, 4);
            if (loginStatusItem) {
                loginStatusItem->setText(loginStatusItem->text() == "NO" ? "YES" : "NO");
                // this->close();

                // QPushButton *button = qobject_cast<QPushButton*>(sender());
                // if (button) {
                //     int row = button->property("row").toInt(); // 假设我们通过某种方式设置了按钮的row属性
                //     QTableWidget *tableWidget = qobject_cast<QTableWidget*>(button->parent()->parent());
                //     if (tableWidget) {
                //         QTableWidgetItem *loginStatusItem = tableWidget->item(row, 4);
                //         if (loginStatusItem) {
                //             loginStatusItem->setText(loginStatusItem->text() == "NO" ? "YES" : "NO");
                //         }
                //     }
                // }

                // tableWidget->viewport()->update();
            }
        }
        else{
            QMessageBox::information(this, "提示", "服务器返回更改失败", QMessageBox::Yes);
        }
    }

    void getDetails(QJsonObject jsonObj){

        // 模拟用户数据
        // QMap<QString, QVariant> userData = {
        //     {"email", "user1@example.com"},
        //     {"name", "user1"},
        //     {"phone", "1234567890"},
        //     {"ai_operations_count", 10},
        //     {"can_login", "不可以登录"}
        // };



        // 遍历JSON对象
        for (auto it = jsonObj.begin(); it != jsonObj.end(); ++it) {
            QMap<QString, QVariant> userData;

            QString email = it.key(); // 用户邮箱作为键
            QJsonObject userInfo = it.value().toObject(); // 用户信息作为值

            // 将JSON对象转换为QVariantMap
            QVariantMap userInfoMap;
            int row = 0;
            for (auto userInfoIt = userInfo.begin(); userInfoIt != userInfo.end(); ++userInfoIt) {
                // QString key = userInfoIt.key();
                // QVariant value = userInfoIt.value().toVariant();
                // userInfoMap.insert(key, value);

                QString key = userInfoIt.key();
                QVariant value = userInfoIt.value().toVariant();
                userData[key] = value;
            }

            // 将用户信息添加到QMap中
            // userData.insert(email, userInfoMap);

            // 添加用户数据到表格
            if(userData["phone"] != "15033355555")
                addUserToTable(tableWidget, userData);
        }

        // 将表格添加到布局中
        QVBoxLayout *layout = new QVBoxLayout(this);
        layout->addWidget(tableWidget);
        this->setLayout(layout);

    }

private:
    void addUserToTable(QTableWidget *tableWidget, const QMap<QString, QVariant> &userData) {
        int row = tableWidget->rowCount();
        tableWidget->insertRow(row);

        // 添加用户信息
        tableWidget->setItem(row, 0, new QTableWidgetItem(userData["email"].toString()));
        tableWidget->setItem(row, 1, new QTableWidgetItem(userData["name"].toString()));
        tableWidget->setItem(row, 2, new QTableWidgetItem(userData["phone"].toString()));
        tableWidget->setItem(row, 3, new QTableWidgetItem(userData["ai_operations_count"].toString())); //QString::number(
        tableWidget->setItem(row, 4, new QTableWidgetItem(userData["can_login"].toString()));

        // 添加登录按钮
        QPushButton *loginButton = new QPushButton("更改登录状态");
        // 为按钮设置属性，以便在槽函数中使用
        loginButton->setProperty("row", row);
        connect(loginButton, &QPushButton::clicked, this, &UserListWidget::onLoginButtonClicked);
        tableWidget->setCellWidget(row, 5, loginButton);
    }

    int _click_row;

    PostManager* _postManager;
    PostManager* _post_login_state;

    QTableWidget *tableWidget;
};

#endif // USERLIST_H
