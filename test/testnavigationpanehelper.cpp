/*
 * SPDX-FileCopyrightText: 2026 MSHost contributors
 * SPDX-License-Identifier: GPL-2.0-or-later
 */

#include "config.h"
#include "navigationpanehelper.h"

#include <QTest>

using namespace Qt::StringLiterals;

class TestNavigationPaneHelper : public QObject
{
    Q_OBJECT

private Q_SLOTS:
    void ownsNamespaceEntry_data()
    {
        QTest::addColumn<QString>("applicationName");
        QTest::addColumn<bool>("owned");
        const auto configuredName = QString::fromUtf8(APPLICATION_NAME);
        QTest::newRow("current-application") << configuredName << true;
        QTest::newRow("upstream-nextcloud") << u"Nextcloud"_s << false;
        QTest::newRow("other-brand") << u"Other-Cloud"_s << false;
        QTest::newRow("empty-name") << QString{} << false;
        QTest::newRow("similar-name") << configuredName + u"Dev"_s << false;
        QTest::newRow("different-case") << configuredName.toLower() << false;
    }

    void ownsNamespaceEntry()
    {
        QFETCH(QString, applicationName);
        QFETCH(bool, owned);
        QCOMPARE(OCC::NavigationPaneHelper::ownsNamespaceEntry(applicationName), owned);
    }
};

QTEST_GUILESS_MAIN(TestNavigationPaneHelper)
#include "testnavigationpanehelper.moc"
