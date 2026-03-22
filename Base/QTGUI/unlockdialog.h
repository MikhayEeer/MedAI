#ifndef UNLOCKDIALOG_H
#define UNLOCKDIALOG_H

#include "qSlicerBaseQTGUIExport.h"

#include <QDialog>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QVBoxLayout>
#include <QHBoxLayout> // 新增：用于布局
#include <QMessageBox>
#include <QNetworkInterface>
#include <QHostInfo>
#include <QCryptographicHash>
#include <QStandardPaths>
#include <QDir>
#include <QFile>
#include <QTextStream>
#include <QCloseEvent> // 【重要】新增：必须包含此头文件才能使用 QCloseEvent

class Q_SLICER_BASE_QTGUI_EXPORT UnlockDialog : public QDialog
{
    Q_OBJECT

public:
    explicit UnlockDialog(QWidget *parent = nullptr);

    // 获取机器唯一ID
    static QString getMachineID();

    // 验证逻辑
    bool verifyAndSaveLicense(const QString &key);

protected:
    // 【重要】新增：声明 closeEvent 函数，以便重写 Qt 的关闭事件
    void closeEvent(QCloseEvent *event) override;

private:
    void initUI();

    QLabel *lblInstruction;
    QLabel *lblMachineID;
    QLineEdit *editKey;
    QPushButton *btnUnlock;
    QPushButton *btnCancel;
    QVBoxLayout *mainLayout;

    const QString SECRET_SALT = "MySuperSecretCompanySalt2026";
};

#endif // UNLOCKDIALOG_H
