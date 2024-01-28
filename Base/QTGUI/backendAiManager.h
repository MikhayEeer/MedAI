#ifndef BACKEND_AI_PROCESSING_MANAGER_H
#define BACKEND_AI_PROCESSING_MANAGER_H

#pragma execution_character_set("utf-8")
#include <QObject>
#include <QWidget>
#include <QDialog>
#include <QLabel>
#include <QLineEdit>
#include <QComboBox>
#include <QPushButton>
#include <QHBoxLayout>
#include <QVBoxLayout>
#include <QProgressDialog>
#include <QSettings>
#include <QNetworkAccessManager>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QFile>
#include <QFileDialog>
#include <QtNetwork>
#include <QHttpMultiPart>
#include <QMessageBox>
#include "qSlicerBaseQTGUIExport.h"

class Q_SLICER_BASE_QTGUI_EXPORT backendAiManager : public QWidget
{
    Q_OBJECT
public:
    explicit backendAiManager(QWidget *parent = nullptr);
    ~backendAiManager();

    enum AI_MODEL {
        AIRWAY = 0,
        VESSEL = 1,
    };

    void choose_file_for_airway();
    void choose_file_for_vessel();

private:
    void uploadFile(QStringList files, AI_MODEL kind);

    QLabel      *userNameLbl;
    QLabel      *pwdLbl;

	QPushButton* airwayBtn;      //airway按钮
	QPushButton* vessel_button;
	//    QPushButton *exitBtn;        //退出按钮
	QProgressDialog* m_progress;
	QString m_result_path;

	QHttpMultiPart* multiPart;
	QNetworkReply* reply;
	QNetworkAccessManager* manager;
	QMessageBox* finishedDialog;

	void initUI();


};

#endif // BACKEND_AI_PROCESSING_MANAGER_H
