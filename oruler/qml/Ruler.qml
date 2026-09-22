// The ruler: drag to measure a distance, click to measure whatever is under the
// pointer. This overlay *does* take input — it is a measuring tool, and a click is
// the measurement — so it says so by using a crosshair cursor and leaving on Escape.
import Quickshell
import Quickshell.Wayland
import Quickshell.Io
import QtQuick

ShellRoot {
  id: root

  readonly property var options: JSON.parse(Quickshell.env("OMARCHY_RULER_OPTIONS") || "{}")
  readonly property color accent: options.accent || "#ff5555"
  readonly property int thickness: options.thickness || 2

  property bool dragging: false
  property real x1: 0
  property real y1: 0
  property real x2: 0
  property real y2: 0
  property string readout: "drag to measure · click to measure what is under the pointer"
  property var box: null                 // { left, top, width, height } from `bounds`

  function measured() {
    return Math.abs(x2 - x1) + " × " + Math.abs(y2 - y1) + " px"
  }

  PanelWindow {
    id: panel
    visible: true
    anchors { top: true; bottom: true; left: true; right: true }
    color: "transparent"
    WlrLayershell.namespace: "omarchy-screen-ruler"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
    exclusionMode: ExclusionMode.Ignore

    // ---------------------------------------------------------------- the box found by `bounds`
    Rectangle {
      visible: root.box !== null && !root.dragging
      x: root.box ? root.box.left : 0
      y: root.box ? root.box.top : 0
      width: root.box ? root.box.width : 0
      height: root.box ? root.box.height : 0
      color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.15)
      border.color: root.accent
      border.width: root.thickness
    }

    // ---------------------------------------------------------------- the drag
    Rectangle {
      visible: root.dragging
      x: Math.min(root.x1, root.x2)
      y: Math.min(root.y1, root.y2)
      width: Math.abs(root.x2 - root.x1)
      height: Math.abs(root.y2 - root.y1)
      color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.12)
      border.color: root.accent
      border.width: root.thickness
    }
    // Lines out to the edges, so the measurement can be lined up with something far away.
    Rectangle {
      visible: root.dragging
      x: 0; width: parent.width
      y: root.y2 - root.thickness / 2; height: root.thickness
      color: root.accent; opacity: 0.4
    }
    Rectangle {
      visible: root.dragging
      y: 0; height: parent.height
      x: root.x2 - root.thickness / 2; width: root.thickness
      color: root.accent; opacity: 0.4
    }

    // ---------------------------------------------------------------- the readout
    Rectangle {
      id: label
      x: Math.min(Math.max(8, root.x2 + 18), parent.width - width - 8)
      y: Math.min(Math.max(8, root.y2 + 18), parent.height - height - 8)
      width: labelText.width + 24; height: labelText.height + 16
      radius: 8
      color: "#e6000000"
      border.color: root.accent
      border.width: 1
      Text {
        id: labelText
        anchors.centerIn: parent
        text: root.readout
        color: "#ffffff"
        font.pixelSize: 16
        font.family: "monospace"
      }
    }

    MouseArea {
      anchors.fill: parent
      hoverEnabled: true
      cursorShape: Qt.CrossCursor
      acceptedButtons: Qt.LeftButton | Qt.RightButton

      onPressed: (event) => {
        if (event.button === Qt.RightButton) { root.box = null; return }
        root.x1 = event.x; root.y1 = event.y
        root.x2 = event.x; root.y2 = event.y
        root.dragging = true
        root.box = null
      }

      onPositionChanged: (event) => {
        root.x2 = event.x; root.y2 = event.y
        if (root.dragging) {
          measureProcess.command = ["omarchy-screen-ruler", "measure", "--json",
                                    String(Math.round(root.x1)), String(Math.round(root.y1)),
                                    String(Math.round(root.x2)), String(Math.round(root.y2))]
          if (!measureProcess.running) measureProcess.running = true
        }
      }

      onReleased: (event) => {
        if (event.button === Qt.RightButton) return
        const moved = Math.abs(root.x2 - root.x1) > 3 || Math.abs(root.y2 - root.y1) > 3
        root.dragging = false
        if (!moved) {
          // A click with no drag asks what is underneath — the Bounds measurement.
          boundsProcess.command = ["omarchy-screen-ruler", "bounds", "--json",
                                   String(Math.round(event.x)), String(Math.round(event.y))]
          boundsProcess.running = true
        }
      }
    }

    Item {
      anchors.fill: parent
      focus: true
      Keys.onPressed: (event) => {
        if (event.key === Qt.Key_Escape) Qt.quit()
        else if (event.text.toLowerCase() === "c" && (event.modifiers & Qt.ControlModifier)) {
          copyProcess.command = ["sh", "-c",
            "printf '%s' " + JSON.stringify(root.readout) + " | wl-copy"]
          copyProcess.running = true
          root.readout = root.readout + "  (copied)"
        }
        event.accepted = true
      }
    }
  }

  // The measuring itself is the CLI's job: it has the captured pixels and the monitor
  // geometry, and it is the part with tests around it.
  Process {
    id: measureProcess
    stdout: SplitParser {
      onRead: (line) => {
        try { root.readout = JSON.parse(line).label } catch (e) { }
      }
    }
  }

  Process {
    id: boundsProcess
    stdout: SplitParser {
      onRead: (line) => {
        try {
          const found = JSON.parse(line)
          root.box = found
          root.readout = found.label
        } catch (e) { }
      }
    }
  }

  Process { id: copyProcess }
}
