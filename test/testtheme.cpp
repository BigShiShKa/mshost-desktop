/*
 * SPDX-FileCopyrightText: 2021 Nextcloud GmbH and Nextcloud contributors
 * SPDX-License-Identifier: GPL-2.0-or-later
 */

#include <QTest>

#include "config.h"
#include "iconutils.h"
#include "logger.h"
#include "theme.h"
#include "themeutils.h"

#include <QImage>
#include <QPixmap>
#include <QStandardPaths>
#include <QUrl>

using namespace Qt::StringLiterals;

class TestTheme : public QObject
{
    Q_OBJECT

public:
    TestTheme()
    {
        Q_INIT_RESOURCE(resources);
        Q_INIT_RESOURCE(theme);
    }

private Q_SLOTS:
    void initTestCase()
    {
        OCC::Logger::instance()->setLogFlush(true);
        OCC::Logger::instance()->setLogDebug(true);

        QStandardPaths::setTestModeEnabled(true);
    }

    void testWizardHideSelfHostButtonMatchesBranding()
    {
        const auto theme = OCC::Theme::instance();
        const auto hidden = static_cast<bool>(WIZARD_HIDE_SELF_HOST_BUTTON);

        QCOMPARE(theme->wizardHideSelfHostButton(), hidden);
        QCOMPARE(theme->property("wizardHideSelfHostButton").toBool(), hidden);
    }

    void testWizardSignupMatchesBranding()
    {
        const auto theme = OCC::Theme::instance();
        const auto hidden = static_cast<bool>(WIZARD_HIDE_SIGNUP_BUTTON);

        QCOMPARE(theme->wizardHideSignupButton(), hidden);
        QCOMPARE(theme->property("wizardHideSignupButton").toBool(), hidden);
#ifdef APPLICATION_SIGNUP_URL
        const auto configured = QString::fromUtf8(APPLICATION_SIGNUP_URL);
#else
        const auto configured = QString();
#endif
        QCOMPARE(theme->wizardSignupUrl(), OCC::Theme::signupUrlForBranding(configured));
    }

    void testSignupUrlForBranding_data()
    {
        QTest::addColumn<QString>("configured");
        QTest::addColumn<QUrl>("expected");

        const auto defaultUrl = QUrl(QString::fromUtf8(APPLICATION_SERVER_URL));
        const auto custom = u"https://signup.example.com/register?plan=business&source=desktop"_s;
        const auto http = u"http://signup.example.com:8080/register"_s;
        const auto encoded = u"https://signup.example.com/register?next=%2Ffiles&offer=$monthly#plans"_s;
        const auto encodedBraces = u"https://signup.example.com/register?offer=$%7Bcloud%7D;trial=1"_s;
        QTest::newRow("empty uses default") << QString() << defaultUrl;
        QTest::newRow("custom HTTPS") << custom << QUrl(custom);
        QTest::newRow("custom HTTP") << http << QUrl(http);
        QTest::newRow("query and fragment preserved") << encoded << QUrl(encoded);
        QTest::newRow("encoded query characters") << encodedBraces << QUrl(encodedBraces);
        QTest::newRow("relative URL") << u"/register"_s << defaultUrl;
        QTest::newRow("missing host") << u"https:///register"_s << defaultUrl;
        QTest::newRow("file URL") << u"file:///tmp/register"_s << defaultUrl;
        QTest::newRow("javascript URL") << u"javascript:alert(1)"_s << defaultUrl;
        QTest::newRow("invalid escape") << u"https://signup.example.com/%zz"_s << defaultUrl;
        QTest::newRow("unencoded braces") << u"https://signup.example.com/register?offer=${cloud}"_s << defaultUrl;
        QTest::newRow("credentials") << u"https://user:password@signup.example.com/register"_s << defaultUrl;
        QTest::newRow("empty credentials") << u"https://@signup.example.com/register"_s << defaultUrl;
        QTest::newRow("leading whitespace") << u" https://signup.example.com/register"_s << defaultUrl;
        QTest::newRow("trailing whitespace") << u"https://signup.example.com/register "_s << defaultUrl;
        QTest::newRow("line break") << u"https://signup.example.com/reg\nister"_s << defaultUrl;
    }

    void testSignupUrlForBranding()
    {
        QFETCH(QString, configured);
        QFETCH(QUrl, expected);

        QCOMPARE(OCC::Theme::signupUrlForBranding(configured), expected);
    }

    void testMSHostLinks_data()
    {
        QTest::addColumn<QString>("actual");
        QTest::addColumn<QString>("expected");
        const auto theme = OCC::Theme::instance();
        const auto server = QString::fromUtf8(APPLICATION_SERVER_URL);
        const auto help = QString::fromUtf8(APPLICATION_HELP_URL);
        QTest::newRow("server-hint") << theme->wizardUrlHint() << server;
        QTest::newRow("signup-fallback") << OCC::Theme::signupUrlForBranding({}).toString() << server;
        QTest::newRow("help") << theme->helpUrl() << help;
        QTest::newRow("conflict-help") << theme->conflictHelpUrl() << help;
    }

    void testMSHostLinks()
    {
        QFETCH(QString, actual);
        QFETCH(QString, expected);
        QCOMPARE(actual, expected);
    }

    void testMSHostSourceLink()
    {
        const auto details = OCC::Theme::instance()->gitSHA1();
        QVERIFY(!details.contains(u"github.com/nextcloud/"_s));
        QVERIFY(details.contains(u"github.com/BigShiShKa/mshost-desktop/commit/"_s));
    }

    void testMSHostCloudOnlySetup()
    {
        const auto theme = OCC::Theme::instance();
        QVERIFY(theme->wizardHideSignupButton());
        QVERIFY(theme->wizardHideSelfHostButton());
    }

    void testMSHostTrayLogo_data()
    {
        QTest::addColumn<int>("status");
        QTest::addColumn<bool>("mono");
        for (const auto mono : {false, true}) {
            for (const auto status : {-1,
                                      int(OCC::SyncResult::Success),
                                      int(OCC::SyncResult::SyncRunning),
                                      int(OCC::SyncResult::Paused),
                                      int(OCC::SyncResult::Problem),
                                      int(OCC::SyncResult::Error),
                                      int(OCC::SyncResult::Undefined),
                                      int(OCC::SyncResult::SetupError)}) {
                const auto name = QString::number(status) + (mono ? u"-mono"_s : u"-color"_s);
                QTest::newRow(qPrintable(name)) << status << mono;
            }
        }
    }

    void testMSHostTrayLogo()
    {
        QFETCH(int, status);
        QFETCH(bool, mono);
        const auto theme = OCC::Theme::instance();
        theme->setSystrayUseMonoIcons(mono);
        const auto icon = status == -1 ? theme->folderOfflineIcon(true) : theme->syncStateIcon(static_cast<OCC::SyncResult::Status>(status), true);
        constexpr auto iconSize = 64;
        const auto image = icon.pixmap(iconSize, iconSize).toImage();
        QVERIFY(!image.isNull());
        QCOMPARE(image.pixelColor(0, 0).alpha(), 0);
        auto cyanPixels = 0;
        auto purplePixels = 0;
        for (auto y = 0; y < image.height(); ++y) {
            for (auto x = 0; x < image.width(); ++x) {
                const auto color = image.pixelColor(x, y);
                if (color.alpha() < 128) {
                    continue;
                }
                cyanPixels += color.red() < 90 && color.green() > 130 && color.blue() > 130;
                purplePixels += color.red() > 90 && color.green() < 100 && color.blue() > 130;
            }
        }
        constexpr auto minimumBrandPixels = 10;
        QVERIFY2(cyanPixels >= minimumBrandPixels && purplePixels >= minimumBrandPixels, "Every tray state must retain the cyan and purple MSHost cloud logo.");
        theme->setSystrayUseMonoIcons(false);
    }

    void testHidpiFileName_darkBackground_returnPathToWhiteIcon()
    {
        FakePaintDevice paintDevice;
        const QColor backgroundColor("#000000");
        const QString iconName("icon-name");

        const auto iconPath = OCC::Theme::hidpiFileName(iconName + ".png", backgroundColor, &paintDevice);

        QCOMPARE(iconPath, ":/client/theme/white/" + iconName + ".png");
    }

    void testHidpiFileName_lightBackground_returnPathToBlackIcon()
    {
        FakePaintDevice paintDevice;
        const QColor backgroundColor("#ffffff");
        const QString iconName("icon-name");

        const auto iconPath = OCC::Theme::hidpiFileName(iconName + ".png", backgroundColor, &paintDevice);

        QCOMPARE(iconPath, ":/client/theme/black/" + iconName + ".png");
    }

    void testHidpiFileName_hidpiDevice_returnHidpiIconPath()
    {
        FakePaintDevice paintDevice;
        paintDevice.setHidpi(true);
        const QColor backgroundColor("#000000");
        const QString iconName("wizard-files");

        const auto iconPath = OCC::Theme::hidpiFileName(iconName + ".png", backgroundColor, &paintDevice);

        QCOMPARE(iconPath, ":/client/theme/white/" + iconName + "@2x.png");
    }

    void testIsDarkColor_nextcloudBlue_returnTrue()
    {
        const QColor color(0, 130, 201);

        const auto result = OCC::Theme::isDarkColor(color);

        QCOMPARE(result, true);
    }

    void testIsDarkColor_lightColor_returnFalse()
    {
        const QColor color(255, 255, 255);

        const auto result = OCC::Theme::isDarkColor(color);

        QCOMPARE(result, false);
    }

    void testIsDarkColor_darkColor_returnTrue()
    {
        const QColor color(0, 0, 0);

        const auto result = OCC::Theme::isDarkColor(color);

        QCOMPARE(result, true);
    }

    void testIsHidpi_hidpi_returnTrue()
    {
        FakePaintDevice paintDevice;
        paintDevice.setHidpi(true);

        QCOMPARE(OCC::Theme::isHidpi(&paintDevice), true);
    }

    void testIsHidpi_lowdpi_returnFalse()
    {
        FakePaintDevice paintDevice;
        paintDevice.setHidpi(false);

        QCOMPARE(OCC::Theme::isHidpi(&paintDevice), false);
    }
};

QTEST_MAIN(TestTheme)
#include "testtheme.moc"
