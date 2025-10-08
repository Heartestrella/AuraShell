from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, Qt, pyqtProperty, QPoint
from PyQt5.QtWidgets import QWidget, QGraphicsOpacityEffect

class PageTransitionAnimator:
    def __init__(self, duration=500):
        self.duration = duration
        self.animation_group = None
    def slide_fade_transition(self, from_widget: QWidget, to_widget: QWidget, 
                              direction="left", on_finished=None):
        if not from_widget or not to_widget:
            if on_finished:
                on_finished()
            return
        parent = from_widget.parent()
        if not parent:
            if on_finished:
                on_finished()
            return
        width = parent.width()
        height = parent.height()
        to_widget.setGeometry(from_widget.geometry())
        to_widget.show()
        to_widget.raise_()
        from_opacity_effect = QGraphicsOpacityEffect()
        to_opacity_effect = QGraphicsOpacityEffect()
        from_widget.setGraphicsEffect(from_opacity_effect)
        to_widget.setGraphicsEffect(to_opacity_effect)
        self.animation_group = QParallelAnimationGroup()
        from_fade_out = QPropertyAnimation(from_opacity_effect, b"opacity")
        from_fade_out.setDuration(self.duration)
        from_fade_out.setStartValue(1.0)
        from_fade_out.setEndValue(0.0)
        from_fade_out.setEasingCurve(QEasingCurve.InOutCubic)
        from_slide = QPropertyAnimation(from_widget, b"pos")
        from_slide.setDuration(self.duration)
        from_slide.setStartValue(from_widget.pos())
        if direction == "left":
            from_slide.setEndValue(from_widget.pos() + QPoint(-width // 3, 0))
        elif direction == "right":
            from_slide.setEndValue(from_widget.pos() + QPoint(width // 3, 0))
        elif direction == "up":
            from_slide.setEndValue(from_widget.pos() + QPoint(0, -height // 3))
        else:
            from_slide.setEndValue(from_widget.pos() + QPoint(0, height // 3))
        from_slide.setEasingCurve(QEasingCurve.InOutCubic)
        to_fade_in = QPropertyAnimation(to_opacity_effect, b"opacity")
        to_fade_in.setDuration(self.duration)
        to_fade_in.setStartValue(0.0)
        to_fade_in.setEndValue(1.0)
        to_fade_in.setEasingCurve(QEasingCurve.InOutCubic)
        to_slide = QPropertyAnimation(to_widget, b"pos")
        to_slide.setDuration(self.duration)
        if direction == "left":
            to_slide.setStartValue(from_widget.pos() + QPoint(width // 2, 0))
        elif direction == "right":
            to_slide.setStartValue(from_widget.pos() + QPoint(-width // 2, 0))
        elif direction == "up":
            to_slide.setStartValue(from_widget.pos() + QPoint(0, height // 2))
        else:
            to_slide.setStartValue(from_widget.pos() + QPoint(0, -height // 2))
        to_slide.setEndValue(from_widget.pos())
        to_slide.setEasingCurve(QEasingCurve.OutCubic)
        self.animation_group.addAnimation(from_fade_out)
        self.animation_group.addAnimation(from_slide)
        self.animation_group.addAnimation(to_fade_in)
        self.animation_group.addAnimation(to_slide)
        def cleanup():
            from_widget.setGraphicsEffect(None)
            to_widget.setGraphicsEffect(None)
            from_widget.hide()
            if on_finished:
                on_finished()
        self.animation_group.finished.connect(cleanup)
        self.animation_group.start()
    def stop(self):
        if self.animation_group and self.animation_group.state() == QParallelAnimationGroup.Running:
            self.animation_group.stop()
class OpacityHelper(QWidget):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self._opacity = 1.0
    @pyqtProperty(float)
    def opacity(self):
        return self._opacity
    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        self.widget.setWindowOpacity(value)