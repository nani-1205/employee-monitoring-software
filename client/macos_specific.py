# Placeholder for macOS-specific functions
# Requires: pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa
import sys

def get_active_window_title():
    """Gets the title of the currently active window on macOS."""
    if sys.platform != 'darwin':
        return "N/A (Not macOS)"
    try:
        from AppKit import NSWorkspace
        active_app = NSWorkspace.sharedWorkspace().frontmostApplication()
        # Getting window title is more complex, often requires accessibility permissions
        # This gets the app name, which is often sufficient for basic tracking
        return active_app.localizedName() if active_app else "N/A (No active app)"
    except ImportError:
        return "N/A (pyobjc not installed)"
    except Exception as e:
        print(f"Error getting active app name: {e}")
        return "N/A (Error)"

def get_idle_time():
    """Gets the system idle time in seconds on macOS."""
    if sys.platform != 'darwin':
        return 0
    try:
        import Quartz
        idle_time = Quartz.CGEventSourceSecondsSinceLastEventType(
            Quartz.kCGEventSourceStateHIDSystemState,
            Quartz.kCGAnyInputEventType
        )
        return idle_time
    except ImportError:
        return 0
    except Exception:
        return 0 # Error getting idle time