#ifndef DEDUCTIONDIALOG_H
#define DEDUCTIONDIALOG_H

#include "post_manager.h"
#include "qSlicerBaseQTGUIExport.h"

#include <QLabel>
#include <QDialog>
#include <QLineEdit>
#include <QPushButton>
#include <QHBoxLayout>
#include <QVBoxLayout>

#include <QJsonObject>
#include <QJsonDocument>

class Q_SLICER_BASE_QTGUI_EXPORT DeductionDialog : public QDialog
{
    Q_OBJECT
public:
    explicit DeductionDialog(int cost, QString note, QWidget *parent = nullptr);
    void deduction();

signals:
    void deductionAccomplished();

public slots:
    void yesBtn_clicked();
    void noBtn_clicked();
    void finishedDeduction(QJsonObject);

private:
    void initUI();
    int m_cost;
    QString m_note;

    PostManager* _postManager;

    QLabel *m_tip;
    QPushButton *m_yesBtn;
    QPushButton *m_noBtn;
};

#endif // DEDUCTIONDIALOG_H
