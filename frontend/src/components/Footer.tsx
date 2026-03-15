import { Scale, Heart } from "lucide-react";

const Footer = () => {
  return (
    <footer className="mt-auto border-t border-border bg-muted/30">
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row items-center justify-between space-y-4 md:space-y-0">
          <div className="flex items-center space-x-2">
            <Scale className="h-5 w-5 text-primary" />
            <span className="text-sm font-medium text-muted-foreground">
              Smart Legal Assistant
            </span>
          </div>
          
          <div className="text-center text-sm text-muted-foreground">
            © {new Date().getFullYear()} Smart Legal Assistant. All rights reserved.
          </div>
          
          
        </div>
      </div>
    </footer>
  );
};

export default Footer;