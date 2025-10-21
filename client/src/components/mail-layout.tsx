import { useState } from "react";
import { Mail, LogOut, Inbox, CheckSquare, Star, FileText, Send as SendIcon, Archive, Trash, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import InboxReminder from "./layers/inbox-reminder";
import TaskSchedule from "./layers/task-schedule";
import CategoryDetail from "./layers/category-detail";
import Chatbot from "./layers/chatbot";
import CustomizePriorities from "./layers/customize-priorities";
import FlaggedMails from "./layers/flagged-mails";

// Layer types for right panel navigation
export type Layer = 
  | { type: "inbox-reminder" }
  | { type: "task-schedule" }
  | { type: "category-detail"; category: "urgent" | "todo" | "fyi" }
  | { type: "chatbot"; from?: Layer }
  | { type: "customize-priorities" }
  | { type: "flagged-mails" };

interface MailLayoutProps {
  children?: React.ReactNode;
  userEmail?: string;
  onLogout?: () => void;
}

export default function MailLayout({ children, userEmail, onLogout }: MailLayoutProps) {
  const [currentLayer, setCurrentLayer] = useState<Layer>({ type: "inbox-reminder" });

  // Navigation handlers
  const handleCategoryClick = (category: "urgent" | "todo" | "fyi") => {
    setCurrentLayer({ type: "category-detail", category });
  };

  const handleChatbotClick = () => {
    setCurrentLayer({ type: "chatbot", from: currentLayer });
  };

  const handleAddTagsClick = () => {
    setCurrentLayer({ type: "customize-priorities" });
  };

  const handleFlaggedClick = () => {
    setCurrentLayer({ type: "flagged-mails" });
  };

  const handleBack = () => {
    if (currentLayer.type === "chatbot" && currentLayer.from) {
      setCurrentLayer(currentLayer.from);
    } else {
      setCurrentLayer({ type: "inbox-reminder" });
    }
  };

  const handleTaskScheduleSwitch = () => {
    setCurrentLayer({ type: "task-schedule" });
  };

  const handleInboxReminderSwitch = () => {
    setCurrentLayer({ type: "inbox-reminder" });
  };

  const handleRefresh = () => {
    // TODO: Implement refresh logic
    console.log("Refresh clicked");
  };

  const handleFinishCustomize = () => {
    setCurrentLayer({ type: "inbox-reminder" });
  };

  // Render current layer
  const renderLayer = () => {
    switch (currentLayer.type) {
      case "inbox-reminder":
        return (
          <InboxReminder
            unreadCount={21}
            onCategoryClick={handleCategoryClick}
            onAddTagsClick={handleAddTagsClick}
            onFlaggedClick={handleFlaggedClick}
            onRefreshClick={handleRefresh}
            onTaskScheduleClick={handleTaskScheduleSwitch}
          />
        );
      case "task-schedule":
        return (
          <TaskSchedule
            onFlaggedClick={handleFlaggedClick}
            onRefreshClick={handleRefresh}
            onInboxReminderClick={handleInboxReminderSwitch}
          />
        );
      case "category-detail":
        return (
          <CategoryDetail
            category={currentLayer.category}
            onBack={handleBack}
            onChatbotClick={handleChatbotClick}
          />
        );
      case "chatbot":
        return <Chatbot onBack={handleBack} />;
      case "customize-priorities":
        return (
          <CustomizePriorities
            onBack={handleBack}
            onFinish={handleFinishCustomize}
          />
        );
      case "flagged-mails":
        return (
          <FlaggedMails
            onBack={handleBack}
            onChatbotClick={handleChatbotClick}
          />
        );
    }
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Left Sidebar - Gmail Navigation */}
      <aside className="w-48 border-r border-border bg-sidebar flex flex-col">
        <div className="p-4 border-b border-sidebar-border">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
              <Mail className="w-5 h-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="font-semibold text-sm">AIMailPilot</h1>
              {userEmail && (
                <p className="text-xs text-muted-foreground truncate">{userEmail}</p>
              )}
            </div>
          </div>
        </div>
        
        <nav className="flex-1 overflow-y-auto p-2">
          <div className="space-y-1">
            <NavItem icon={Inbox} label="Inbox" count={21} active />
            <NavItem icon={CheckSquare} label="To-Do" count={6} />
            <NavItem icon={Star} label="Starred" />
            <NavItem icon={FileText} label="Draft" />
            <NavItem icon={SendIcon} label="Sent" />
            <NavItem icon={Archive} label="Archive" />
            <NavItem icon={Trash} label="Trash" />
          </div>
        </nav>

        <div className="p-4 border-t border-sidebar-border space-y-2">
          <button className="w-full text-left text-sm px-3 py-2 rounded-lg hover-elevate flex items-center gap-2" data-testid="button-settings">
            <Settings className="w-4 h-4" />
            <span>Settings</span>
          </button>
          {onLogout && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onLogout}
              className="w-full justify-start"
              data-testid="button-logout"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          )}
        </div>
      </aside>

      {/* Middle Panel - Email List */}
      <main className="w-96 border-r border-border flex flex-col bg-background">
        <header className="h-14 border-b border-border px-4 flex items-center gap-2">
          <input 
            type="search" 
            placeholder="Search emails..." 
            className="flex-1 px-3 py-1.5 text-sm rounded-md bg-muted border-0 focus:ring-2 focus:ring-primary focus:outline-none"
            data-testid="input-search"
          />
        </header>
        
        <div className="flex gap-1 px-4 py-2 border-b border-border">
          <button className="px-3 py-1 text-sm font-medium rounded-md bg-primary text-primary-foreground" data-testid="button-filter-important">
            Important <span className="ml-1">11</span>
          </button>
          <button className="px-3 py-1 text-sm rounded-md hover-elevate" data-testid="button-filter-updates">
            Updates <span className="ml-1 text-muted-foreground">552</span>
          </button>
          <button className="px-3 py-1 text-sm rounded-md hover-elevate" data-testid="button-filter-promotions">
            Promotions <span className="ml-1 text-muted-foreground">115</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {children}
        </div>
      </main>

      {/* Right Sidebar - AIMailPilot Panel */}
      <aside className="flex-1 flex flex-col bg-background overflow-hidden">
        <div className="flex-1 overflow-y-auto p-6">
          {renderLayer()}
        </div>
      </aside>
    </div>
  );
}

interface NavItemProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  count?: number;
  active?: boolean;
}

function NavItem({ icon: Icon, label, count, active }: NavItemProps) {
  return (
    <button
      className={`
        w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors
        ${active 
          ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium" 
          : "text-sidebar-foreground hover-elevate"
        }
      `}
      data-testid={`nav-${label.toLowerCase()}`}
    >
      <Icon className="w-4 h-4" />
      <span className="flex-1 text-left">{label}</span>
      {count !== undefined && (
        <span className={`text-xs ${active ? "text-primary font-semibold" : "text-muted-foreground"}`}>
          {count}
        </span>
      )}
    </button>
  );
}
