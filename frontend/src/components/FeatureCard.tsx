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
    primary: "hover:shadow-primary/20 hover:border-primary",
    secondary: "hover:shadow-secondary/20 hover:border-secondary",
    accent: "hover:shadow-accent/20 hover:border-accent",
  };
  
  const iconColors = {
    primary: "text-primary",
    secondary: "text-secondary",
    accent: "text-accent",
  };
  
  return (
    <Link to={link}>
      <div className={`group relative overflow-hidden rounded-xl border border-border bg-card p-6 transition-all duration-300 hover:scale-105 hover:shadow-xl ${colorStyles[color]} animate-fade-up`}>
        <div className="absolute inset-0 gradient-card opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        
        <div className="relative z-10">
          <div className={`mb-4 inline-flex rounded-lg bg-muted p-3 ${iconColors[color]} group-hover:scale-110 transition-transform duration-300`}>
            <Icon className="h-6 w-6" />
          </div>
          
          <h3 className="mb-2 text-xl font-bold text-foreground">
            {title}
          </h3>
          
          <p className="text-sm text-muted-foreground">
            {description}
          </p>
          
          <div className="mt-4 flex items-center text-sm font-medium text-primary">
            <span>Learn more</span>
            <svg
              className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
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