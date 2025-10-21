import { ArrowLeft, Mail, Edit, Plus } from "lucide-react";

interface CustomizePrioritiesProps {
  onBack: () => void;
  onFinish: () => void;
}

export default function CustomizePriorities({ onBack, onFinish }: CustomizePrioritiesProps) {
  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-gradient-to-br from-primary/20 to-primary/10 p-4 flex items-center gap-3 mb-6 rounded-2xl">
        <button 
          onClick={onBack}
          className="p-2 hover:bg-primary/10 rounded-lg transition-colors"
          data-testid="button-back"
        >
          <ArrowLeft className="w-5 h-5 text-primary" />
        </button>
        <div className="flex items-center gap-2 text-primary">
          <Mail className="w-5 h-5" />
          <span className="font-semibold">AIMailPilot</span>
        </div>
      </div>

      {/* Title */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-foreground">Customize Priorities</h2>
        <button className="text-sm text-primary flex items-center gap-1 hover:underline" data-testid="button-sort">
          Sort ↕
        </button>
      </div>

      {/* Tag List */}
      <div className="flex-1 space-y-4">
        <PriorityTag label="Urgent" color="bg-secondary" />
        <PriorityTag label="To-do" color="bg-accent" />
        <PriorityTag label="FYI" color="bg-secondary" />
        
        <button
          className="w-full p-5 rounded-2xl border-2 border-dashed border-border hover:bg-card transition-colors flex items-center justify-center gap-2"
          data-testid="button-add-more-tags"
        >
          <Plus className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Add more tags</span>
        </button>
      </div>

      {/* Finish Button */}
      <button
        onClick={onFinish}
        className="mt-6 w-48 mx-auto px-8 py-3 rounded-full border-2 border-primary text-primary hover:bg-primary hover:text-primary-foreground transition-all font-medium"
        data-testid="button-finish"
      >
        Finish
      </button>
    </div>
  );
}

interface PriorityTagProps {
  label: string;
  color: string;
}

function PriorityTag({ label, color }: PriorityTagProps) {
  return (
    <div className="flex items-center gap-3">
      <div className={`${color} rounded-full px-6 py-3 flex-1 text-primary font-medium`}>
        {label}
      </div>
      <button className="p-2 hover:bg-card rounded-lg transition-colors" data-testid={`button-edit-${label.toLowerCase()}`}>
        <Edit className="w-5 h-5 text-muted-foreground" />
      </button>
    </div>
  );
}
