import { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  link: string;
  color: "primary" | "secondary" | "accent";
}

const FeatureCard = ({ icon: Icon, title, description, link, color }: FeatureCardProps) => {
  const colorStyles = {
    primary: {
      bg: "from-blue-50 to-cyan-50",
      border: "hover:border-primary",
      shadow: "hover:shadow-primary/30",
      icon: "bg-gradient-to-br from-primary to-primary/80 text-white",
      accent: "group-hover:text-primary",
    },
    secondary: {
      bg: "from-cyan-50 to-teal-50",
      border: "hover:border-secondary",
      shadow: "hover:shadow-secondary/30",
      icon: "bg-gradient-to-br from-secondary to-secondary/80 text-white",
      accent: "group-hover:text-secondary",
    },
    accent: {
      bg: "from-orange-50 to-yellow-50",
      border: "hover:border-accent",
      shadow: "hover:shadow-accent/30",
      icon: "bg-gradient-to-br from-accent to-accent/80 text-white",
      accent: "group-hover:text-accent",
    },
  };
  
  const currentColors = colorStyles[color];
  
  return (
    <Link to={link}>
      <div className={`group relative overflow-hidden rounded-2xl border-2 border-border bg-gradient-to-br ${currentColors.bg} backdrop-blur-sm p-8 transition-all duration-300 hover:scale-105 hover:shadow-2xl ${currentColors.border} ${currentColors.shadow} animate-fade-up hover:-translate-y-1`}>
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-br from-white/50 to-transparent pointer-events-none" />
        
        <div className="relative z-10">
          <div className={`mb-6 inline-flex rounded-xl p-4 ${currentColors.icon} group-hover:scale-110 transition-transform duration-300 shadow-lg`}>
            <Icon className="h-8 w-8" />
          </div>
          
          <h3 className="mb-3 text-2xl font-black text-foreground tracking-tight">
            {title}
          </h3>
          
          <p className="text-base text-muted-foreground leading-relaxed mb-6 font-medium">
            {description}
          </p>          
          <div className={`flex items-center text-base font-bold transition-all duration-300 ${currentColors.accent}`}>
            <span>Learn more</span>
            <svg
              className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.5}
                d="M13 7l5 5m0 0l-5 5m5-5H6"
              />
            </svg>
          </div>
        </div>
      </div>
    </Link>
  );
};

export default FeatureCard;