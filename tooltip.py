"""
Tooltip module for Docling GUI
Provides a simple way to add hover tooltips to tkinter widgets
"""
import tkinter as tk


class ToolTip:
    """
    Create a tooltip for a given widget with hover functionality.
    """

    def __init__(self, widget, text, delay=500):
        """
        Initialize the tooltip.

        Args:
            widget: The tkinter widget to attach the tooltip to
            text: The tooltip text to display
            delay: Delay in milliseconds before showing tooltip (default: 500)
        """
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.after_id = None

        # Bind events
        self.widget.bind('<Enter>', self.on_enter)
        self.widget.bind('<Leave>', self.on_leave)
        self.widget.bind('<Button>', self.on_leave)  # Hide on click

    def on_enter(self, _event=None):
        """Schedule tooltip to appear after delay"""
        self.schedule_tooltip()

    def on_leave(self, _event=None):
        """Cancel scheduled tooltip and hide if visible"""
        self.cancel_tooltip()
        self.hide_tooltip()

    def schedule_tooltip(self):
        """Schedule the tooltip to appear after the delay"""
        self.cancel_tooltip()
        self.after_id = self.widget.after(self.delay, self.show_tooltip)

    def cancel_tooltip(self):
        """Cancel the scheduled tooltip"""
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

    def show_tooltip(self):
        """Display the tooltip"""
        if self.tooltip_window:
            return

        # Get widget position
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        # Create tooltip window
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        # Create tooltip label with styling
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            background="#ffffd0",
            foreground="#000000",
            relief=tk.SOLID,
            borderwidth=1,
            font=("", 9),
            padx=8,
            pady=4,
            justify=tk.LEFT
        )
        label.pack()

    def hide_tooltip(self):
        """Hide the tooltip"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def create_tooltip(widget, text, delay=500):
    """
    Convenience function to create a tooltip for a widget.

    Args:
        widget: The tkinter widget to attach the tooltip to
        text: The tooltip text to display
        delay: Delay in milliseconds before showing tooltip (default: 500)

    Returns:
        ToolTip instance
    """
    return ToolTip(widget, text, delay)
