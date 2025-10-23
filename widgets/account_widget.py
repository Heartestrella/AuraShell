import os
import random
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout
from qfluentwidgets import (
    CardWidget, SimpleCardWidget, AvatarWidget, TitleLabel, CaptionLabel,
    StrongBodyLabel, BodyLabel, PillPushButton, PrimaryPushButton,
    ProgressRing, InfoBar, InfoBarPosition
)
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest


class ApiUsageCard(CardWidget):
    def __init__(self, title, used, total, unit, parent=None):
        super().__init__(parent)
        self.used = used
        self.total = total
        self.unit = unit
        self.setFixedHeight(120)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        text_layout = QVBoxLayout()
        text_layout.setAlignment(Qt.AlignLeft)

        self.title_label = TitleLabel(self.tr(title))
        self.title_label.setStyleSheet("TitleLabel { font-size: 16px; }")

        self.usage_label = BodyLabel(
            self.tr(f"{self.used} / {self.total} {self.unit}"))
        self.usage_label.setStyleSheet(
            "BodyLabel { color: #666; font-size: 14px; }")

        self.percent_label = StrongBodyLabel(
            self.tr(f"{self.get_percentage():.1f}%"))
        self.percent_label.setStyleSheet(
            "StrongBodyLabel { font-size: 18px; color: #0078d4; }")

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.usage_label)
        text_layout.addStretch(1)
        text_layout.addWidget(self.percent_label)

        self.progress_ring = ProgressRing(self)
        self.progress_ring.setTextVisible(True)
        self.progress_ring.setFixedSize(80, 80)
        self.progress_ring.setValue(int(self.get_percentage()))

        layout.addLayout(text_layout)
        layout.addStretch(1)
        layout.addWidget(self.progress_ring)

        self.update_display()

    def get_percentage(self):
        return (self.used / self.total) * 100 if self.total else 0

    def update_display(self):
        self.usage_label.setText(
            self.tr(f"{self.used:,} / {self.total:,} {self.unit}"))
        self.percent_label.setText(self.tr(f"{self.get_percentage():.1f}%"))
        self.progress_ring.setValue(int(self.get_percentage()))
        p = self.get_percentage()
        color = "#d13438" if p > 90 else "#ffaa44" if p > 70 else "#0078d4"
        self.percent_label.setStyleSheet(
            f"StrongBodyLabel {{ font-size: 18px; color: {color}; }}")


class AccountInfoCard(SimpleCardWidget):
    def __init__(self, username=None, qid=None, email=None, avatar_url=None, combo=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(140)
        self.setContentsMargins(15, 16, 15, 16)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)

        self.avatar = AvatarWidget()
        self.avatar.setFixedSize(64, 64)
        layout.addWidget(self.avatar, 0, Qt.AlignVCenter)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(0, 5, 0, 5)

        name = username or self.tr("Guest")
        upgrade_text = self.tr("Login") if username == self.tr(
            "Guest") else self.tr("Upgrade")
        self.name_label = TitleLabel(name, self)
        self.name_label.setStyleSheet("font-size: 18px; font-weight: 600;")

        self.qid_label = CaptionLabel(
            self.tr(f"QID: {qid}") if qid else self.tr("QID: "), self)
        self.email_label = CaptionLabel(email or "", self)
        self.email_label.setStyleSheet("color: #666;")
        self.combo = CaptionLabel(self.tr(f"{combo}") if combo else "", self)

        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.qid_label)
        info_layout.addWidget(self.email_label)
        info_layout.addWidget(self.combo)
        info_layout.addStretch(1)

        layout.addLayout(info_layout, stretch=1)

        button_layout = QVBoxLayout()
        button_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.upgrade_btn = PillPushButton(upgrade_text)
        self.upgrade_btn.setFixedWidth(110)
        button_layout.addWidget(self.upgrade_btn)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)

        self.qid_label.setVisible(bool(qid))
        self.email_label.setVisible(bool(email))
        self.combo.setVisible(bool(combo))

        self._network_manager = QNetworkAccessManager()
        self._tmp_avatar_file = None
        self._set_avatar(username, avatar_url)

    def _set_avatar(self, username, avatar_url):
        print(avatar_url)
        if self._tmp_avatar_file and os.path.exists(self._tmp_avatar_file):
            try:
                os.remove(self._tmp_avatar_file)
            except:
                pass
            self._tmp_avatar_file = None

        if avatar_url and avatar_url.startswith("http"):
            request = QNetworkRequest(QUrl(avatar_url))
            reply = self._network_manager.get(request)
            self._current_reply = reply
            reply.finished.connect(
                lambda r=reply, u=username: self._on_avatar_downloaded(r, u))
        elif avatar_url and os.path.exists(avatar_url):
            self.avatar.setImage(avatar_url)
        else:
            self._set_default_avatar(username)

    def _on_avatar_downloaded(self, reply, username):
        if hasattr(self, '_current_reply') and self._current_reply == reply:
            self._current_reply = None
        if reply.error():
            self._set_default_avatar(username)
            reply.deleteLater()
            return
        data = reply.readAll()
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self.avatar.setPixmap(pixmap)
        else:
            self._set_default_avatar(username)
        reply.deleteLater()

    def _set_default_avatar(self, username):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#D0D0D0"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 64, 64)
        painter.setPen(QColor("#555"))
        painter.setFont(QFont("Segoe UI", 20, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter,
                         (username[:1] if username else "G").upper())
        painter.end()
        self.avatar.setPixmap(pixmap)

    def update_account_info(self, username=None, qid=None, email=None, combo=None, avatar_url=None):
        self.name_label.setText(username or self.tr("Guest"))

        if qid:
            self.qid_label.setText(self.tr(f"QID: {qid}"))
            self.qid_label.setVisible(True)
        else:
            self.qid_label.setVisible(False)

        if email:
            self.email_label.setText(email)
            self.email_label.setVisible(True)
        else:
            self.email_label.setVisible(False)

        if combo:
            self.combo.setText(self.tr(str(combo)))
            self.combo.setVisible(True)
        else:
            self.combo.setVisible(False)

        self.upgrade_btn.setText(self.tr("Login") if username == self.tr(
            "Guest") else self.tr("Upgrade"))
        self._set_avatar(username, avatar_url)


class BillingCard(CardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        title_label = TitleLabel(self.tr("Account Balance"))
        title_label.setStyleSheet("TitleLabel { font-size: 16px; }")

        balance_layout = QHBoxLayout()
        self.balance_label = StrongBodyLabel(self.tr("¥ 0.00"))
        self.balance_label.setStyleSheet(
            "StrongBodyLabel { font-size: 24px; color: #107c10; }")
        # self.recharge_btn = PrimaryPushButton(self.tr("Recharge Now"))
        # self.recharge_btn.setFixedWidth(100)

        balance_layout.addWidget(self.balance_label)
        balance_layout.addStretch(1)
        # balance_layout.addWidget(self.recharge_btn)

        self.billing_label = CaptionLabel(self.tr("Next billing date: None"))
        self.billing_label.setStyleSheet("CaptionLabel { color: #666; }")

        layout.addWidget(title_label)
        layout.addSpacing(10)
        layout.addLayout(balance_layout)
        layout.addSpacing(5)
        layout.addWidget(self.billing_label)


class AccountPage(QWidget):
    def __init__(self, username=None, qid=None, email=None,  avatar_url=None, combo=None, parent=None):
        super().__init__(parent)
        self.username = username
        self.qid = qid
        self.email = email
        self.avatar_url = avatar_url
        self.combo = combo
        self.setup_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(5000)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(30, 20, 30, 20)

        title_label = TitleLabel(self.tr("Account Information"))
        title_label.setStyleSheet(
            "TitleLabel { font-size: 24px; padding: 10px 0; }")

        self.account_card = AccountInfoCard(
            username=self.username, qid=self.qid, email=self.email, avatar_url=self.avatar_url, combo=self.combo
        )

        usage_grid = QGridLayout()
        usage_grid.setSpacing(15)
        self.api_cards = [
            ApiUsageCard("API Calls", 1250, 5000, "times"),
            ApiUsageCard("Tokens Usage", 850000, 1000000, "tokens"),
        ]
        for i, card in enumerate(self.api_cards):
            row, col = divmod(i, 2)
            usage_grid.addWidget(card, row, col)

        self.billing_card = BillingCard()
        layout.addWidget(title_label)
        layout.addWidget(self.account_card)
        layout.addSpacing(10)
        layout.addLayout(usage_grid)
        layout.addSpacing(10)
        layout.addWidget(self.billing_card)
        layout.addStretch(1)
        self.connect_signals()

    def connect_signals(self):
        # self.billing_card.recharge_btn.clicked.connect(
        #     self.show_recharge_dialog)
        self.account_card.upgrade_btn.clicked.connect(self.show_upgrade_dialog)

    def show_recharge_dialog(self):
        InfoBar.info(
            title=self.tr("Recharge Function"),
            content=self.tr("Recharge function is under development..."),
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=2000, parent=self
        )

    def show_upgrade_dialog(self):
        InfoBar.info(
            title=self.tr("Upgrade Account"),
            content=self.tr(
                "Account upgrade function is under development..."),
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=2000, parent=self
        )

    def update_data(self):
        for card in self.api_cards:
            increment = random.randint(1, 10)
            card.used = min(card.used + increment, card.total)
            card.update_display()
        current_balance_text = self.billing_card.balance_label.text().replace(
            "¥ ", "").replace(self.tr("¥ "), "")
        try:
            current_balance = float(current_balance_text)
            new_balance = current_balance + random.uniform(0.01, 0.1)
            self.billing_card.balance_label.setText(
                self.tr(f"¥ {new_balance:.2f}"))
        except ValueError:
            self.billing_card.balance_label.setText(self.tr("¥ 0.00"))

    def update_account_info(self, username=None, qid=None, email=None, combo=None, avatar_url=None):
        self.username, self.qid, self.email, self.avatar_url = username, qid, email, avatar_url
        self.account_card.update_account_info(
            username=username, qid=qid, email=email, combo=combo, avatar_url=avatar_url
        )
