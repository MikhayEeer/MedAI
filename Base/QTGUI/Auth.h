#ifndef AUTH_H
#define AUTH_H

#include <QProcess>
#include <QString>
#include <QDialog>
#include <QNetworkInterface>
#include <QtWidgets>
#include <QtGUI>


#include "qSlicerBaseQTGUIExport.h"

class Q_SLICER_BASE_QTGUI_EXPORT AuthForm : public QDialog{
	Q_OBJECT
public:
	explicit AuthForm(QWidget* parent = nullptr);
	~AuthForm();
	bool whetherAuthPassed();
private:
	QString getCPUSerialNumber();
	QString getMACAddress();
	bool auth_right;
};
#endif // !AUTH_H