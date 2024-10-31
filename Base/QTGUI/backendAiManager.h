#ifndef BACKEND_AI_MANAGER_H
#define BACKEND_AI_MANAGER_H

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
#include "post_manager.h"

// DICOM匿名化相关头文件
#include <QProgressBar>
#include <QInputDialog>
#include "dcmtk/config/osconfig.h"
#include "dcmtk/dcmdata/dctk.h"


#pragma execution_character_set("utf-8")

class Q_SLICER_BASE_QTGUI_EXPORT Backend_AI_Processing_manager : public QWidget
{
    Q_OBJECT
public:
    explicit Backend_AI_Processing_manager(QString filePath = "", QWidget *parent = nullptr);
    ~Backend_AI_Processing_manager();

    enum AI_MODEL {
        AIRWAY = 0,
        VESSEL = 1,
        VESSELV2 = 2,
    };

    void add_ai_ops();
    void choose_file_for_airway();
    void choose_file_for_vessel();
    void choose_file_for_vesselV2();

signals:
    void signal_add_finish();

public slots:
    void finishedAdd(QJsonObject m_res);

private:
    void uploadFile();

    QStringList _choosed_files;
    AI_MODEL _choosed_model;
    // 用于增加ai操作次数（同时可以作验证）
    PostManager* _postManager;



    QLabel      *userNameLbl;
    QLabel      *pwdLbl;

    QPushButton *airwayBtn;      //airway按钮
    QPushButton *vessel_button;
    QPushButton *vessel_v2_button;
	//    QPushButton *exitBtn;        //退出按钮
	QProgressDialog *m_progress;
	QString m_result_path;

	QHttpMultiPart* multiPart;
	QNetworkReply* reply;
	QNetworkAccessManager* manager;
	QMessageBox* finishedDialog;

	void initUI();
};

class Q_SLICER_BASE_QTGUI_EXPORT DicomAnonymizer : public QDialog {
    Q_OBJECT
public:
    explicit DicomAnonymizer(QWidget *parent = nullptr);
    ~DicomAnonymizer();

signals:
    void anonymizationFinished();

public slots:
    void onImportButtonClicked();
    void onAnonymizeButtonClicked();
    void onCancelButtonClicked();

private:
    void initUI();
    void anonymizeDicom(const QString& dicomPath, const QString& patientName);
    
    QPushButton* importButton;
    QPushButton* anonymizeButton; 
    QPushButton* cancelButton;
    QLabel* statusLabel;
    QProgressBar* progressBar;
    
    QString selectedDicomPath;
    QStringList dicomFiles;
};

#endif // BACKEND_AI_MANAGER_H
