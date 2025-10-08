from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QSequentialAnimationGroup, Qt, pyqtProperty, QPoint, QRect
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
    def zoom_in_transition(self, from_widget: QWidget, to_widget: QWidget, 
                          scale_from=0.3, with_fade=True, on_finished=None):
        if not from_widget or not to_widget:
            if on_finished:
                on_finished()
            return
        parent = from_widget.parent()
        if not parent:
            if on_finished:
                on_finished()
            return
        to_widget.setGeometry(from_widget.geometry())
        to_widget.show()
        to_widget.raise_()
        from_opacity_effect = QGraphicsOpacityEffect()
        to_opacity_effect = QGraphicsOpacityEffect()
        from_widget.setGraphicsEffect(from_opacity_effect)
        to_widget.setGraphicsEffect(to_opacity_effect)
        self.animation_group = QParallelAnimationGroup()
        if with_fade:
            from_fade_out = QPropertyAnimation(from_opacity_effect, b"opacity")
            from_fade_out.setDuration(self.duration)
            from_fade_out.setStartValue(1.0)
            from_fade_out.setEndValue(0.0)
            from_fade_out.setEasingCurve(QEasingCurve.InOutCubic)
            self.animation_group.addAnimation(from_fade_out)
        to_fade_in = QPropertyAnimation(to_opacity_effect, b"opacity")
        to_fade_in.setDuration(self.duration)
        to_fade_in.setStartValue(0.0)
        to_fade_in.setEndValue(1.0)
        to_fade_in.setEasingCurve(QEasingCurve.OutCubic)
        original_geometry = to_widget.geometry()
        center_x = original_geometry.center().x()
        center_y = original_geometry.center().y()
        start_width = int(original_geometry.width() * scale_from)
        start_height = int(original_geometry.height() * scale_from)
        start_x = center_x - start_width // 2
        start_y = center_y - start_height // 2
        to_scale = QPropertyAnimation(to_widget, b"geometry")
        to_scale.setDuration(self.duration)
        to_scale.setStartValue(QRect(start_x, start_y, start_width, start_height))
        to_scale.setEndValue(original_geometry)
        to_scale.setEasingCurve(QEasingCurve.OutCubic)
        self.animation_group.addAnimation(to_fade_in)
        self.animation_group.addAnimation(to_scale)
        def cleanup():
            from_widget.setGraphicsEffect(None)
            to_widget.setGraphicsEffect(None)
            from_widget.hide()
            to_widget.setGeometry(original_geometry)
            if on_finished:
                on_finished()
        self.animation_group.finished.connect(cleanup)
        self.animation_group.start()
    def zoom_out_transition(self, from_widget: QWidget, to_widget: QWidget,
                           scale_to=0.3, with_fade=True, on_finished=None):
        if not from_widget or not to_widget:
            if on_finished:
                on_finished()
            return
        parent = from_widget.parent()
        if not parent:
            if on_finished:
                on_finished()
            return
        to_widget.setGeometry(from_widget.geometry())
        to_widget.show()
        to_widget.raise_()
        from_widget.raise_()
        from_opacity_effect = QGraphicsOpacityEffect()
        to_opacity_effect = QGraphicsOpacityEffect()
        from_widget.setGraphicsEffect(from_opacity_effect)
        to_widget.setGraphicsEffect(to_opacity_effect)
        self.animation_group = QParallelAnimationGroup()
        to_fade_in = QPropertyAnimation(to_opacity_effect, b"opacity")
        to_fade_in.setDuration(self.duration)
        to_fade_in.setStartValue(0.0)
        to_fade_in.setEndValue(1.0)
        to_fade_in.setEasingCurve(QEasingCurve.InOutCubic)
        original_geometry = from_widget.geometry()
        center_x = original_geometry.center().x()
        center_y = original_geometry.center().y()
        end_width = int(original_geometry.width() * scale_to)
        end_height = int(original_geometry.height() * scale_to)
        end_x = center_x - end_width // 2
        end_y = center_y - end_height // 2
        from_scale = QPropertyAnimation(from_widget, b"geometry")
        from_scale.setDuration(self.duration)
        from_scale.setStartValue(original_geometry)
        from_scale.setEndValue(QRect(end_x, end_y, end_width, end_height))
        from_scale.setEasingCurve(QEasingCurve.InCubic)
        if with_fade:
            from_fade_out = QPropertyAnimation(from_opacity_effect, b"opacity")
            from_fade_out.setDuration(self.duration)
            from_fade_out.setStartValue(1.0)
            from_fade_out.setEndValue(0.0)
            from_fade_out.setEasingCurve(QEasingCurve.InCubic)
            self.animation_group.addAnimation(from_fade_out)
        self.animation_group.addAnimation(to_fade_in)
        self.animation_group.addAnimation(from_scale)
        def cleanup():
            from_widget.setGraphicsEffect(None)
            to_widget.setGraphicsEffect(None)
            from_widget.hide()
            from_widget.setGeometry(original_geometry)
            if on_finished:
                on_finished()
        self.animation_group.finished.connect(cleanup)
        self.animation_group.start()
    def cross_fade_transition(self, from_widget: QWidget, to_widget: QWidget, on_finished=None):
        if not from_widget or not to_widget:
            if on_finished:
                on_finished()
            return
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
        to_fade_in = QPropertyAnimation(to_opacity_effect, b"opacity")
        to_fade_in.setDuration(self.duration)
        to_fade_in.setStartValue(0.0)
        to_fade_in.setEndValue(1.0)
        to_fade_in.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation_group.addAnimation(from_fade_out)
        self.animation_group.addAnimation(to_fade_in)
        def cleanup():
            from_widget.setGraphicsEffect(None)
            to_widget.setGraphicsEffect(None)
            from_widget.hide()
            if on_finished:
                on_finished()
        self.animation_group.finished.connect(cleanup)
        self.animation_group.start()
    def bounce_transition(self, from_widget: QWidget, to_widget: QWidget,
                          direction="up", bounce_height=0.3, on_finished=None):
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
        from_fade_out.setEasingCurve(QEasingCurve.InCubic)
        to_fade_in = QPropertyAnimation(to_opacity_effect, b"opacity")
        to_fade_in.setDuration(self.duration)
        to_fade_in.setStartValue(0.0)
        to_fade_in.setEndValue(1.0)
        to_fade_in.setEasingCurve(QEasingCurve.OutBounce)
        to_bounce = QPropertyAnimation(to_widget, b"pos")
        to_bounce.setDuration(self.duration)
        if direction == "up":
            to_bounce.setStartValue(from_widget.pos() + QPoint(0, int(height * bounce_height)))
        elif direction == "down":
            to_bounce.setStartValue(from_widget.pos() + QPoint(0, int(-height * bounce_height)))
        elif direction == "left":
            to_bounce.setStartValue(from_widget.pos() + QPoint(int(width * bounce_height), 0))
        else:
            to_bounce.setStartValue(from_widget.pos() + QPoint(int(-width * bounce_height), 0))
        to_bounce.setEndValue(from_widget.pos())
        to_bounce.setEasingCurve(QEasingCurve.OutBounce)
        self.animation_group.addAnimation(from_fade_out)
        self.animation_group.addAnimation(to_fade_in)
        self.animation_group.addAnimation(to_bounce)
        def cleanup():
            from_widget.setGraphicsEffect(None)
            to_widget.setGraphicsEffect(None)
            from_widget.hide()
            if on_finished:
                on_finished()
        self.animation_group.finished.connect(cleanup)
        self.animation_group.start()
    def elastic_transition(self, from_widget: QWidget, to_widget: QWidget,
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
        from_fade_out.setEasingCurve(QEasingCurve.InCubic)
        from_slide = QPropertyAnimation(from_widget, b"pos")
        from_slide.setDuration(self.duration)
        from_slide.setStartValue(from_widget.pos())
        if direction == "left":
            from_slide.setEndValue(from_widget.pos() + QPoint(-width // 4, 0))
        elif direction == "right":
            from_slide.setEndValue(from_widget.pos() + QPoint(width // 4, 0))
        elif direction == "up":
            from_slide.setEndValue(from_widget.pos() + QPoint(0, -height // 4))
        else:
            from_slide.setEndValue(from_widget.pos() + QPoint(0, height // 4))
        from_slide.setEasingCurve(QEasingCurve.InCubic)
        to_fade_in = QPropertyAnimation(to_opacity_effect, b"opacity")
        to_fade_in.setDuration(self.duration)
        to_fade_in.setStartValue(0.0)
        to_fade_in.setEndValue(1.0)
        to_fade_in.setEasingCurve(QEasingCurve.OutElastic)
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
        to_slide.setEasingCurve(QEasingCurve.OutElastic)
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
    def fade_scale_transition(self, from_widget: QWidget, to_widget: QWidget,
                              scale_direction="in", on_finished=None):
        if not from_widget or not to_widget:
            if on_finished:
                on_finished()
            return
        parent = from_widget.parent()
        if not parent:
            if on_finished:
                on_finished()
            return
        to_widget.setGeometry(from_widget.geometry())
        to_widget.show()
        to_widget.raise_()
        from_widget.raise_()
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
        to_fade_in = QPropertyAnimation(to_opacity_effect, b"opacity")
        to_fade_in.setDuration(self.duration)
        to_fade_in.setStartValue(0.0)
        to_fade_in.setEndValue(1.0)
        to_fade_in.setEasingCurve(QEasingCurve.InOutCubic)
        original_geometry = to_widget.geometry()
        center_x = original_geometry.center().x()
        center_y = original_geometry.center().y()
        if scale_direction == "in":
            start_width = int(original_geometry.width() * 0.8)
            start_height = int(original_geometry.height() * 0.8)
        else:
            start_width = int(original_geometry.width() * 1.2)
            start_height = int(original_geometry.height() * 1.2)
        start_x = center_x - start_width // 2
        start_y = center_y - start_height // 2
        to_scale = QPropertyAnimation(to_widget, b"geometry")
        to_scale.setDuration(self.duration)
        to_scale.setStartValue(QRect(start_x, start_y, start_width, start_height))
        to_scale.setEndValue(original_geometry)
        to_scale.setEasingCurve(QEasingCurve.InOutCubic)
        from_geom = from_widget.geometry()
        from_center_x = from_geom.center().x()
        from_center_y = from_geom.center().y()
        if scale_direction == "in":
            end_width = int(from_geom.width() * 1.2)
            end_height = int(from_geom.height() * 1.2)
        else:
            end_width = int(from_geom.width() * 0.8)
            end_height = int(from_geom.height() * 0.8)
        end_x = from_center_x - end_width // 2
        end_y = from_center_y - end_height // 2
        from_scale = QPropertyAnimation(from_widget, b"geometry")
        from_scale.setDuration(self.duration)
        from_scale.setStartValue(from_geom)
        from_scale.setEndValue(QRect(end_x, end_y, end_width, end_height))
        from_scale.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation_group.addAnimation(from_fade_out)
        self.animation_group.addAnimation(to_fade_in)
        self.animation_group.addAnimation(to_scale)
        self.animation_group.addAnimation(from_scale)
        def cleanup():
            from_widget.setGraphicsEffect(None)
            to_widget.setGraphicsEffect(None)
            from_widget.hide()
            from_widget.setGeometry(from_geom)
            to_widget.setGeometry(original_geometry)
            if on_finished:
                on_finished()
        self.animation_group.finished.connect(cleanup)
        self.animation_group.start()
    def slide_scale_transition(self, from_widget: QWidget, to_widget: QWidget,
                              direction="left", scale_factor=0.9, on_finished=None):
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
        from_fade_out.setEndValue(0.3)
        from_fade_out.setEasingCurve(QEasingCurve.InOutCubic)
        from_slide = QPropertyAnimation(from_widget, b"pos")
        from_slide.setDuration(self.duration)
        from_slide.setStartValue(from_widget.pos())
        if direction == "left":
            from_slide.setEndValue(from_widget.pos() + QPoint(-width // 4, 0))
        elif direction == "right":
            from_slide.setEndValue(from_widget.pos() + QPoint(width // 4, 0))
        elif direction == "up":
            from_slide.setEndValue(from_widget.pos() + QPoint(0, -height // 4))
        else:
            from_slide.setEndValue(from_widget.pos() + QPoint(0, height // 4))
        from_slide.setEasingCurve(QEasingCurve.InOutCubic)
        from_geom = from_widget.geometry()
        from_center_x = from_geom.center().x()
        from_center_y = from_geom.center().y()
        scale_width = int(from_geom.width() * scale_factor)
        scale_height = int(from_geom.height() * scale_factor)
        scale_x = from_center_x - scale_width // 2
        scale_y = from_center_y - scale_height // 2
        from_scale = QPropertyAnimation(from_widget, b"geometry")
        from_scale.setDuration(self.duration)
        from_scale.setStartValue(from_geom)
        from_scale.setEndValue(QRect(scale_x, scale_y, scale_width, scale_height))
        from_scale.setEasingCurve(QEasingCurve.InOutCubic)
        to_fade_in = QPropertyAnimation(to_opacity_effect, b"opacity")
        to_fade_in.setDuration(self.duration)
        to_fade_in.setStartValue(0.0)
        to_fade_in.setEndValue(1.0)
        to_fade_in.setEasingCurve(QEasingCurve.InOutCubic)
        to_slide = QPropertyAnimation(to_widget, b"pos")
        to_slide.setDuration(self.duration)
        if direction == "left":
            to_slide.setStartValue(from_widget.pos() + QPoint(width, 0))
        elif direction == "right":
            to_slide.setStartValue(from_widget.pos() + QPoint(-width, 0))
        elif direction == "up":
            to_slide.setStartValue(from_widget.pos() + QPoint(0, height))
        else:
            to_slide.setStartValue(from_widget.pos() + QPoint(0, -height))
        to_slide.setEndValue(from_widget.pos())
        to_slide.setEasingCurve(QEasingCurve.OutCubic)
        self.animation_group.addAnimation(from_fade_out)
        self.animation_group.addAnimation(from_slide)
        self.animation_group.addAnimation(from_scale)
        self.animation_group.addAnimation(to_fade_in)
        self.animation_group.addAnimation(to_slide)
        def cleanup():
            from_widget.setGraphicsEffect(None)
            to_widget.setGraphicsEffect(None)
            from_widget.hide()
            from_widget.setGeometry(from_geom)
            if on_finished:
                on_finished()
        self.animation_group.finished.connect(cleanup)
        self.animation_group.start()
    def stack_transition(self, from_widget: QWidget, to_widget: QWidget,
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
        from_widget.raise_()
        from_opacity_effect = QGraphicsOpacityEffect()
        to_opacity_effect = QGraphicsOpacityEffect()
        from_widget.setGraphicsEffect(from_opacity_effect)
        to_widget.setGraphicsEffect(to_opacity_effect)
        to_opacity_effect.setOpacity(1.0)
        self.animation_group = QParallelAnimationGroup()
        from_slide = QPropertyAnimation(from_widget, b"pos")
        from_slide.setDuration(self.duration)
        from_slide.setStartValue(from_widget.pos())
        if direction == "left":
            from_slide.setEndValue(from_widget.pos() + QPoint(-width, 0))
        elif direction == "right":
            from_slide.setEndValue(from_widget.pos() + QPoint(width, 0))
        elif direction == "up":
            from_slide.setEndValue(from_widget.pos() + QPoint(0, -height))
        else:
            from_slide.setEndValue(from_widget.pos() + QPoint(0, height))
        from_slide.setEasingCurve(QEasingCurve.InOutCubic)
        from_fade_out = QPropertyAnimation(from_opacity_effect, b"opacity")
        from_fade_out.setDuration(self.duration)
        from_fade_out.setStartValue(1.0)
        from_fade_out.setEndValue(0.0)
        from_fade_out.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation_group.addAnimation(from_slide)
        self.animation_group.addAnimation(from_fade_out)
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
class ScaleHelper(QWidget):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self._scale = 1.0
        self._original_geometry = widget.geometry()
    @pyqtProperty(float)
    def scale(self):
        return self._scale
    @scale.setter
    def scale(self, value):
        self._scale = value
        self._apply_scale()
    def _apply_scale(self):
        if not self.widget:
            return
        center = self._original_geometry.center()
        new_width = int(self._original_geometry.width() * self._scale)
        new_height = int(self._original_geometry.height() * self._scale)
        new_x = center.x() - new_width // 2
        new_y = center.y() - new_height // 2
        self.widget.setGeometry(new_x, new_y, new_width, new_height)
class AnimationConfig:
    def __init__(self):
        self.presets = {
            "fast": {"duration": 200, "easing": QEasingCurve.OutCubic},
            "normal": {"duration": 500, "easing": QEasingCurve.InOutCubic},
            "slow": {"duration": 800, "easing": QEasingCurve.InOutQuad},
            "bounce": {"duration": 600, "easing": QEasingCurve.OutBounce},
            "elastic": {"duration": 800, "easing": QEasingCurve.OutElastic},
            "smooth": {"duration": 400, "easing": QEasingCurve.InOutQuad},
        }
    def get_preset(self, name):
        return self.presets.get(name, self.presets["normal"])
    def add_preset(self, name, duration, easing):
        self.presets[name] = {"duration": duration, "easing": easing}