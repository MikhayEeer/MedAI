#include "unlockdialog.h"

#include <QCoreApplication>
#include <QDebug>
#include <QTimer>

UnlockDialog::UnlockDialog(QWidget *parent)
    : QDialog(parent)
{
    setWindowTitle("系统安全验证");
    setModal(true); // 模态窗口，阻塞其他操作
    setFixedSize(500, 400);

    initUI();

    // 如果已经存在有效的许可证，直接接受并关闭，无需用户操作
    // 但为了演示“前置程序”的感觉，通常我们还是会弹出来确认一下，或者你可以选择直接跳过
    // 这里策略：如果有license，自动通过；如果没有，强制要求输入。
    QString configPath = QCoreApplication::applicationDirPath();
    QFile checkFile(configPath + "/license.dat");

    if (checkFile.exists()) {
        if (verifyAndSaveLicense("")) {
            qDebug() << "success ==================";
            QTimer::singleShot(0, this, [this]() {
                qDebug() << "Auto-accepting dialog..."; // 可选：调试输出
                this->accept();
            });
            return;
        }
    }
}

void UnlockDialog::initUI()
{
    mainLayout = new QVBoxLayout(this);
    mainLayout->setSpacing(15);
    mainLayout->setContentsMargins(10, 10, 10, 10);

    lblInstruction = new QLabel("本软件已授权锁定。\n请输入管理员提供的激活密钥以继续使用。");
    lblInstruction->setWordWrap(true);
    lblInstruction->setStyleSheet("font-size: 14px; font-weight: bold; color: #333;");
    mainLayout->addWidget(lblInstruction);

    QLabel *lblIdTitle = new QLabel("本机识别码 (请复制此ID联系管理员):");
    mainLayout->addWidget(lblIdTitle);

    lblMachineID = new QLabel(getMachineID());
    lblMachineID->setTextInteractionFlags(Qt::TextSelectableByMouse);
    lblMachineID->setStyleSheet("background-color: #eee; padding: 10px; border: 1px solid #ccc; font-family: Consolas;");
    mainLayout->addWidget(lblMachineID);

    mainLayout->addSpacing(10);

    mainLayout->addWidget(new QLabel("激活密钥:"));
    editKey = new QLineEdit();
    editKey->setPlaceholderText("粘贴密钥...");
    editKey->setMinimumHeight(35);
    mainLayout->addWidget(editKey);

    // 按钮布局
    QHBoxLayout *btnLayout = new QHBoxLayout();

    btnUnlock = new QPushButton("验证并解锁");
    btnUnlock->setMinimumHeight(35);
    btnUnlock->setStyleSheet("background-color: #007bff; color: white; font-weight: bold;");
    connect(btnUnlock, &QPushButton::clicked, this, [this]() {
        if (verifyAndSaveLicense(editKey->text())) {
            QMessageBox::information(this, "成功", "验证成功，正在启动程序...");
            accept(); // 关闭对话框，返回 Accepted
        } else {
            QMessageBox::critical(this, "失败", "密钥无效或与此机器不匹配！");
            editKey->clear();
            editKey->setFocus();
        }
    });

    btnCancel = new QPushButton("退出程序");
    btnCancel->setMinimumHeight(35);
    connect(btnCancel, &QPushButton::clicked, this, [this]() {
        int ret = QMessageBox::question(this, "确认退出", "未解锁状态下退出将关闭整个程序。\n确定要退出吗？",
                                        QMessageBox::Yes | QMessageBox::No);
        if (ret == QMessageBox::Yes) {
            reject(); // 关闭对话框，返回 Rejected
        }
    });

    btnLayout->addWidget(btnUnlock);
    btnLayout->addWidget(btnCancel);
    mainLayout->addLayout(btnLayout);
}

QString UnlockDialog::getMachineID()
{
    QList<QNetworkInterface> interfaces = QNetworkInterface::allInterfaces();
    for (const QNetworkInterface &interface : interfaces) {
        if (!(interface.flags() & QNetworkInterface::IsLoopBack) &&
            (interface.flags() & QNetworkInterface::IsRunning)) {
            QString mac = interface.hardwareAddress();
            if (!mac.isEmpty()) {
                return QCryptographicHash::hash(mac.toUtf8(), QCryptographicHash::Sha256).toHex();
            }
        }
    }
    return QCryptographicHash::hash(QHostInfo::localHostName().toUtf8(), QCryptographicHash::Sha256).toHex();
}
bool UnlockDialog::verifyAndSaveLicense(const QString &key)
{
    QString currentMachineID = getMachineID();
    QString expectedHash = QCryptographicHash::hash((currentMachineID + SECRET_SALT).toUtf8(), QCryptographicHash::Sha256).toHex();

    // 【修改点 2】统一使用程序所在目录
    QString configPath = QCoreApplication::applicationDirPath();
    QString filePath = configPath + "/license.dat";

    qDebug() << "=== DEBUG INFO ===";
    qDebug() << "Current App Dir:" << configPath;
    qDebug() << "Checking License File:" << filePath;
    qDebug() << "File Exists:" << QFileInfo(filePath).exists();
    if (QFileInfo(filePath).exists()) {
        qDebug() << "File Size:" << QFileInfo(filePath).size();
        QFile debugFile(filePath);
        if(debugFile.open(QIODevice::ReadOnly)) {
            qDebug() << "File Content:" << debugFile.readAll();
            debugFile.close();
        }
    }
    qDebug() << "==================";

    // 如果是自动检查（key为空），则只读文件验证
    if (key.isEmpty()) {
        QFile file(filePath);
        if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
            return false;
        }

        QTextStream in(&file);
        QString storedHash = in.readLine().trimmed();
        QString storedMachineID = in.readLine().trimmed();
        file.close();

        if (storedMachineID != currentMachineID) {
            // 机器ID不匹配，可能是换了电脑，删除旧文件以免干扰（可选）
            // QFile::remove(filePath);
            return false;
        }
        return (storedHash == expectedHash);
    }
    // 如果是用户输入密钥进行解锁
    else {
        if (key.trimmed() != expectedHash) {
            return false;
        }

        // 保存文件到程序目录
        QFile file(filePath);
        if (file.open(QIODevice::WriteOnly | QIODevice::Text)) {
            QTextStream out(&file);
            out << expectedHash << "\n";
            out << currentMachineID << "\n";
            file.close();
            return true;
        }

        // 如果写入失败，可能是权限问题（例如程序安装在 C:\Program Files）
        // 这里可以加一个错误提示
        QMessageBox::critical(this, "写入失败", "无法在程序目录下创建 license.dat。\n请确保您有该文件夹的写入权限，或以管理员身份运行程序。");
        return false;
    }
}

// 拦截用户点击右上角关闭按钮的行为
void UnlockDialog::closeEvent(QCloseEvent *event)
{
    int ret = QMessageBox::question(this, "确认退出", "程序未解锁，关闭此窗口将退出整个应用程序。\n确定吗？",
                                    QMessageBox::Yes | QMessageBox::No);
    if (ret == QMessageBox::Yes) {
        event->accept();
        // 此时对话框关闭，返回码默认为 Rejected (如果没有调用 accept)
    } else {
        event->ignore();
    }
}
