#include "Auth.h"

#include <QSysInfo>

AuthForm::AuthForm(QWidget* parent)
  : QDialog(parent)
  , auth_right(true)
{
}

AuthForm::~AuthForm() = default;

bool AuthForm::whetherAuthPassed()
{
  return auth_right;
}

QString AuthForm::getCPUSerialNumber()
{
  const QByteArray id = QSysInfo::machineUniqueId();
  return QString::fromLatin1(id.toHex());
}

QString AuthForm::getMACAddress()
{
  const QList<QNetworkInterface> interfaces = QNetworkInterface::allInterfaces();
  for (const QNetworkInterface& iface : interfaces)
  {
    if (!iface.flags().testFlag(QNetworkInterface::IsUp) ||
        iface.flags().testFlag(QNetworkInterface::IsLoopBack))
    {
      continue;
    }

    const QString mac = iface.hardwareAddress();
    if (!mac.isEmpty() && mac != "00:00:00:00:00:00")
    {
      return mac;
    }
  }
  return QString();
}
