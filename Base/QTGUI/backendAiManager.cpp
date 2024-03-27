#include <QNetworkAccessManager>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QFile>
#include <QtNetwork>
#include <QProgressDialog>

#include <QMessageBox>
#include <QJsonObject>
#include <QJsonDocument>
#include <QFileDialog>

#include "UserInfo.h"
#include "backendAiManager.h"

#pragma execution_character_set("utf-8")

backendAiManager::backendAiManager(QWidget* parent)
	: QWidget(parent)
{
	initUI();
	this->setAttribute(Qt::WA_DeleteOnClose);

	m_progress = nullptr;
	multiPart = nullptr;
	reply = nullptr;
	manager = new QNetworkAccessManager(this);
	connect(airwayBtn, &QPushButton::clicked, this, &backendAiManager::choose_file_for_airway);
	connect(vessel_button, &QPushButton::clicked, this, &backendAiManager::choose_file_for_vessel);

}

backendAiManager::~backendAiManager() {
	//    if(m_progress) delete m_progress;
	//    if(multiPart) delete multiPart;
	//    if(reply) delete reply;
	//    if(manager) delete manager;
	//    // 删除对话框
	//    if(finishedDialog) delete finishedDialog;
}

void backendAiManager::choose_file_for_airway() {
	//    this->show();
	QStringList files = QFileDialog::getOpenFileNames(this, tr("选择文件"));
	if (files.length() > 0) {
		uploadFile(files, AI_MODEL::AIRWAY);
		//        QFileDialog m_result_dir;
		//        m_result_dir.setOption(QFileDialog::ShowDirsOnly);
		//        if (m_result_dir.exec()) {
		//            // 用户选择了文件夹
		//            uploadFile(files);
		//        } else {
		//            // 用户关闭了对话框
		//        }
	}
	else {
		if (manager) delete manager;
		this->close();
	}
}

void backendAiManager::choose_file_for_vessel() {
	QStringList files = QFileDialog::getOpenFileNames(this, tr("选择文件"));
	if (files.length() > 0) {
		uploadFile(files, AI_MODEL::VESSEL);
	}
	else {
		if (manager) delete manager;
		this->close();
	}
}

void backendAiManager::uploadFile(QStringList files, AI_MODEL kind) {
	QString filePath = files[0];
	int lastSlashIndex = filePath.lastIndexOf("/");
	// ct文件所在的目录路径
	QString file_dir_path = filePath.left(lastSlashIndex);
	// 文件名
	QString complete_fileName = filePath.mid(lastSlashIndex + 1);
	//    int dotIndex = complete_fileName.lastIndexOf(".");
	int dotIndex = complete_fileName.lastIndexOf(".nii.gz");
	QString baseName = complete_fileName.left(dotIndex);
	m_result_path = file_dir_path + "/气道分割" + baseName + ".nii.gz";
	if (kind == AI_MODEL::VESSEL) {
		m_result_path = file_dir_path + "/肺部血管分割" + baseName + ".nii.gz";
	}
	//    qDebug() << filePath;
	//    qDebug() << file_dir_path;
	//    qDebug() << complete_fileName;
	//    qDebug() << baseName;
	//    qDebug() << m_result_path;


	QNetworkRequest request(QUrl("http://120.224.26.32:13826/upload")); //119.45.186.16 // 127.0.0.1
	if (kind == AI_MODEL::VESSEL) {
		request.setUrl(QUrl("http://120.224.26.32:13826/vessel_ai"));
	}
	multiPart = new QHttpMultiPart(QHttpMultiPart::FormDataType);

	// 网络请求进度窗
	m_progress = new QProgressDialog(this);
	m_progress->setWindowTitle(tr("提示"));
	m_progress->setLabelText(tr("服务器处理中..."));
	m_progress->setCancelButton(nullptr);
	// 不显示右上角的关闭
	m_progress->setWindowFlag(Qt::WindowCloseButtonHint, false);
	m_progress->setRange(0, 100); //设置范围
	m_progress->setModal(true);   //设置为模态对话框
	m_progress->setValue(20); // 假值....
	m_progress->show();

	// 打开要上传的文件
	QFile* file = new QFile(filePath);
	file->open(QIODevice::ReadOnly);
	// 读取所有内容到字节数组
	QByteArray fileData = file->readAll();
	file->close();

	file->deleteLater();
	// 添加文件部分
	QHttpPart filePart;
	filePart.setHeader(QNetworkRequest::ContentTypeHeader, QVariant("application/octet-stream"));
	QString file_name = QString("form-data; name=\"file\"; filename=\"%1\"").arg(file->fileName());
	filePart.setHeader(QNetworkRequest::ContentDispositionHeader, QVariant(file_name));
	filePart.setBody(fileData);
	multiPart->append(filePart);

	// 添加JSON部分
	//    QHttpPart jsonPart;
	//    jsonPart.setHeader(QNetworkRequest::ContentTypeHeader, QVariant("application/json"));
	//    QJsonObject json;
	//    json.insert("name", userInfoEmail);
	//    jsonPart.setBody(QJsonDocument(json).toJson());
	//    multiPart->append(jsonPart);

	reply = manager->post(request, multiPart);
	m_progress->setValue(40); // 假值....

	QEventLoop eventLoop;
	connect(manager, SIGNAL(finished(QNetworkReply*)), &eventLoop, SLOT(quit()));
	eventLoop.exec();

	m_progress->setHidden(true);
	m_progress->setValue(100);

	if (reply->error() != QNetworkReply::NoError) {
		QMessageBox msgBox;
		// 读取并解析错误信息
		QByteArray data = reply->readAll();
		QString errorString = QString::fromUtf8(data);
		qDebug() << "Server Error: " << data;
		qDebug() << reply->errorString();
		if (reply->errorString() == "Connection refused") {
			msgBox.setText(QString("错误：连接服务器失败"));
		}
		else if (reply->errorString() == "Unable to write") {
			msgBox.setText(QString("AI服务器已经满负荷，请5分钟后重试"));
		}
		else {
			msgBox.setText(QString("错误：%1").arg(reply->errorString()));
		}

		msgBox.exec();
		this->close();
		return;
	}

	QFile responseFile(m_result_path);
	if (!responseFile.open(QIODevice::WriteOnly)) {
		QMessageBox msgBox;
		msgBox.setText(QString("服务器传来的文件本地没有读取权限").arg(reply->errorString()));
		msgBox.exec();
		this->close();
		responseFile.close();
		return;
	}

	responseFile.write(reply->readAll());

	finishedDialog = new QMessageBox(QMessageBox::Question, "提示", "处理完成，新文件位于源文件同级目录");

	// 当模型处理完成后，进行提示
	finishedDialog->setWindowFlags(Qt::Dialog);
	QPushButton* agreeBut = finishedDialog->addButton("确认", QMessageBox::AcceptRole);
	QObject::connect(agreeBut, &QPushButton::clicked, this, &backendAiManager::close);

	finishedDialog->exec();
	responseFile.close();
}


void backendAiManager::initUI() {
	this->setWindowTitle(tr("人工智能-自动分割提示窗口"));

	userNameLbl = new QLabel(this);
	userNameLbl->setText("温馨提示:");

	pwdLbl = new QLabel(this);
	pwdLbl->setText("处理时间在5~10分钟");

	airwayBtn = new QPushButton(this);
	airwayBtn->setText(" 气道自动重建 ");

	vessel_button = new QPushButton(this);
	vessel_button->setText("肺部血管自动重建");

	this->setFixedSize(330, 150);
	// 不显示右上角的关闭
	//    setWindowFlag(Qt::WindowCloseButtonHint, false);
	// 不显示右上角的帮助
	setWindowFlag(Qt::WindowContextHelpButtonHint, false);

	QHBoxLayout* HLayout1 = new QHBoxLayout;
	HLayout1->addStretch(1);
	HLayout1->addWidget(userNameLbl, 1);
	HLayout1->addStretch(1);

	QHBoxLayout* HLayout2 = new QHBoxLayout;
	HLayout2->addStretch(1);
	HLayout2->addWidget(pwdLbl, 1);
	HLayout2->addStretch(1);

	QHBoxLayout* HLayout3 = new QHBoxLayout;
	HLayout3->addStretch(1);
	HLayout3->addWidget(airwayBtn, 2);
	HLayout3->addWidget(vessel_button, 2);
	HLayout3->addStretch(1);

	QVBoxLayout* VLayout = new QVBoxLayout(this);
	VLayout->addLayout(HLayout1);
	VLayout->addLayout(HLayout2);
	VLayout->addLayout(HLayout3);
	this->setLayout(VLayout);
}

