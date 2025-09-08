#ifndef PASSWORDDIALOG_H
#define PASSWORDDIALOG_H

#include <QObject>
#include <QDialog>
#include <QLineEdit>
#include <QPushButton>
#include <QLabel>
#include <QVBoxLayout>

#include "userlist.h"
#include "post_manager.h"
#include "qSlicerBaseQTGUIExport.h"

#pragma execution_character_set("utf-8")

class Q_SLICER_BASE_QTGUI_EXPORT PasswordDialog : public QDialog {
    Q_OBJECT

public:
    explicit PasswordDialog(QWidget *parent = nullptr);

private slots:
    void onConfirmClicked();
    void onReturnClicked();
    void finishVerify(QJsonObject);

private:
    QLineEdit *passwordLineEdit;
    QPushButton *confirmButton;
    QPushButton *returnButton;
    QLabel *passwordLabel;
    PostManager* _postManager;
};

#endif // PASSWORDDIALOG_H
