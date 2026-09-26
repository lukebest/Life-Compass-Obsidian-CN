import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "luke.compass"

  property int due: 0
  property int overdue: 0
  property bool paused: false
  property string tooltipBody: "Compass"

  readonly property string stateHome: {
    var state = Quickshell.env("XDG_STATE_HOME")
    if (!state || state === "")
      state = (Quickshell.env("HOME") || "") + "/.local/state"
    return state
  }
  readonly property string statusPath: stateHome + "/compass/status.json"

  function applyStatus(raw) {
    if (!raw || raw.trim() === "")
      return
    try {
      var data = JSON.parse(raw)
      root.due = data.due_today || 0
      root.overdue = data.overdue || 0
      root.paused = data.paused === true
      var lines = []
      var top = data.top || []
      for (var i = 0; i < top.length && i < 3; i++)
        lines.push(top[i])
      var head = root.paused ? "自动化已暂停" : "到期 " + root.due + " · 逾期 " + root.overdue
      root.tooltipBody = lines.length ? head + "\n" + lines.join("\n") : head
    } catch (error) {
    }
  }

  function refresh() {
    if (!readStatus.running)
      readStatus.running = true
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  FileView {
    path: root.statusPath
    watchChanges: true
    printErrors: false
    onFileChanged: root.refresh()
  }

  Timer {
    interval: 60000
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: root.refresh()
  }

  Process {
    id: readStatus
    command: ["sh", "-c", "cat \"$1\" 2>/dev/null || echo '{}'", "compass-status", root.statusPath]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.applyStatus(text)
    }
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.paused ? "\uf14e" : (root.due + "\u00b7" + root.overdue)
    opacity: root.paused ? 0.45 : 1
    slotSize: Style.bar.statusSlot
    fontSize: Style.font.caption
    tooltipText: root.tooltipBody
    onPressed: function(b) {
      if (!root.bar)
        return
      if (b === Qt.RightButton)
        root.bar.run("compass capture")
      else
        root.bar.run("omarchy-menu summon compass")
    }
  }
}
