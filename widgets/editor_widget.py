from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class EditorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_id = None
        self._side_panel = None
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

    def set_tab_id(self, tab_id):
        self.tab_id = tab_id
        print(f"initialized with tab ID: {self.tab_id}")
    
    def _find_side_panel(self):
        if self._side_panel:
            return self._side_panel
        parent = self.parent()
        while parent is not None:
            if parent.metaObject().className() == "SidePanelWidget":
                print("Found and cached SidePanelWidget.")
                self._side_panel = parent
                return self._side_panel
            parent = parent.parent()
        return None

    def get_tab_data(self):
        side_panel = self._find_side_panel()
        if side_panel:
            tab_data = side_panel.get_tab_data_by_uuid(self.tab_id)
            print(f"Retrieved tab data: {tab_data}")
            return tab_data
        return None