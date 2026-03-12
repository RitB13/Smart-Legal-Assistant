import { useState } from "react";
import { ChevronDown, ChevronUp, Shield, Book, Users, Heart, Briefcase, Home } from "lucide-react";
import Layout from "../components/Layout";

interface RightSection {
  id: string;
  title: string;
  icon: React.ReactNode;
  rights: string[];
  description: string;
}

const RightsPage = () => {
  const [expandedSections, setExpandedSections] = useState<string[]>(["fundamental"]);
  
  const rightsSections: RightSection[] = [
    {
      id: "fundamental",
      title: "Fundamental Rights (Articles 12-35)",
      icon: <Shield className="h-5 w-5" />,
      description: "Basic human rights guaranteed by the Constitution of India",
      rights: [
        "Right to Equality (Articles 14-18): Equal treatment before law, prohibition of discrimination, equal opportunity in employment",
        "Right to Freedom (Articles 19-22): Freedom of speech, assembly, movement, residence, profession, protection against arbitrary arrest",
        "Right Against Exploitation (Articles 23-24): Prohibition of human trafficking, forced labor, and child labor",
        "Right to Freedom of Religion (Articles 25-28): Freedom to practice, profess and propagate any religion",
        "Cultural and Educational Rights (Articles 29-30): Protection of minority interests, right to establish educational institutions",
        "Right to Constitutional Remedies (Article 32): Right to approach Supreme Court for enforcement of fundamental rights"
      ]
    },
    {
      id: "legal",
      title: "Legal Rights",
      icon: <Book className="h-5 w-5" />,
      description: "Rights provided by various laws and statutes",
      rights: [
        "Right to Free Legal Aid: Free legal services for poor and marginalized sections",
        "Right to Fair Trial: Presumption of innocence, right to defense lawyer, right to appeal",
        "Right Against Self-Incrimination: Cannot be forced to testify against oneself",
        "Right to Information (RTI Act 2005): Access to government information and records",
        "Right to Privacy: Protection of personal information and data",
        "Right to Bail: Bail is rule, jail is exception (except in serious offenses)",
        "Right to Speedy Trial: Cases must be decided within reasonable time"
      ]
    },
    {
      id: "consumer",
      title: "Consumer Rights",
      icon: <Users className="h-5 w-5" />,
      description: "Protection under Consumer Protection Act 2019",
      rights: [
        "Right to Safety: Protection against hazardous goods and services",
        "Right to Information: Complete information about quality, quantity, price, purity",
        "Right to Choose: Access to variety of goods at competitive prices",
        "Right to be Heard: Grievances to be heard at appropriate forums",
        "Right to Redressal: Compensation for unfair trade practices or defective goods",
        "Right to Consumer Education: Awareness about consumer rights and remedies"
      ]
    },
    {
      id: "women",
      title: "Women's Rights",
      icon: <Heart className="h-5 w-5" />,
      description: "Special protections and rights for women",
      rights: [
        "Right to Equal Pay: Equal remuneration for equal work",
        "Right Against Domestic Violence: Protection from physical, mental, economic abuse",
        "Right to Maternity Benefits: Paid maternity leave up to 26 weeks",
        "Right Against Sexual Harassment: Safe workplace environment, complaint mechanisms",
        "Right to Property: Equal inheritance and property rights",
        "Right to Dignity: Protection against indecent representation and objectification",
        "Right to Free Legal Aid: Priority in legal aid services"
      ]
    },
    {
      id: "worker",
      title: "Worker's Rights",
      icon: <Briefcase className="h-5 w-5" />,
      description: "Labor laws and employment protections",
      rights: [
        "Right to Minimum Wages: Guaranteed minimum wage as per government regulations",
        "Right to Safe Working Conditions: Workplace safety, health measures, accident compensation",
        "Right to Form Unions: Freedom to form and join trade unions",
        "Right to Regulated Working Hours: Maximum 48 hours per week, overtime compensation",
        "Right to Leave: Weekly holidays, casual leave, sick leave, earned leave",
        "Right to Gratuity: Payment after 5 years of continuous service",
        "Right to Provident Fund: Retirement savings scheme with employer contribution"
      ]
    },
    {
      id: "property",
      title: "Property Rights",
      icon: <Home className="h-5 w-5" />,
      description: "Rights related to property ownership and tenancy",
      rights: [
        "Right to Own Property: Buy, sell, inherit property regardless of gender or religion",
        "Right to Peaceful Possession: Protection against illegal eviction or trespassing",
        "Tenant Rights: Fair rent, maintenance, protection against arbitrary eviction",
        "Right to Compensation: Fair compensation for land acquisition by government",
        "Right to Transfer Property: Freedom to sell, gift, or mortgage property",
        "Right Against Encroachment: Legal remedies against illegal occupation"
      ]
    }
  ];
  
  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev =>
      prev.includes(sectionId)
        ? prev.filter(id => id !== sectionId)
        : [...prev, sectionId]
    );
  };
  
  return (
    <Layout>
      <div className="container mx-auto px-4 py-12 max-w-5xl">
        <div className="text-center mb-10 animate-fade-up">
          <h1 className="text-4xl font-bold text-foreground mb-4">
            Know Your Rights
          </h1>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
            Understanding your constitutional and legal rights as an Indian citizen
          </p>
        </div>
        
        <div className="space-y-4">
          {rightsSections.map((section, index) => (
            <div
              key={section.id}
              className="border border-border rounded-xl overflow-hidden bg-card shadow-sm hover:shadow-md transition-all duration-300 animate-fade-up"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <button
                onClick={() => toggleSection(section.id)}
                className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <div className="p-2 rounded-lg bg-primary/10 text-primary">
                    {section.icon}
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-foreground">
                      {section.title}
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      {section.description}
                    </p>
                  </div>
                </div>
                
                <div className="text-muted-foreground">
                  {expandedSections.includes(section.id) ? (
                    <ChevronUp className="h-5 w-5" />
                  ) : (
                    <ChevronDown className="h-5 w-5" />
                  )}
                </div>
              </button>
              
              {expandedSections.includes(section.id) && (
                <div className="px-6 pb-4 border-t border-border animate-slide-up">
                  <ul className="space-y-3 mt-4">
                    {section.rights.map((right, rightIndex) => (
                      <li
                        key={rightIndex}
                        className="flex items-start space-x-2 text-sm animate-fade-in"
                        style={{ animationDelay: `${rightIndex * 0.05}s` }}
                      >
                        <div className="w-1.5 h-1.5 rounded-full bg-primary mt-2 flex-shrink-0" />
                        <span className="text-foreground/90">{right}</span>
                      </li>
                    ))}
                  </ul>
                  
                  <div className="mt-6 p-4 bg-primary/5 border border-primary/20 rounded-lg">
                    <p className="text-sm text-muted-foreground">
                      <strong className="text-primary">Remember:</strong> These rights are protected by law.
                      If you believe your rights have been violated, seek legal counsel or approach the appropriate authorities.
                    </p>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
        
        <div className="mt-12 text-center p-6 bg-gradient-to-r from-primary/10 to-secondary/10 rounded-xl border border-primary/20 animate-fade-up">
          <h3 className="text-lg font-semibold text-foreground mb-2">
            Need Legal Help?
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            If you need assistance understanding or exercising your rights, our AI assistant is here to help.
          </p>
          <a href="/chat">
            <button className="inline-flex items-center justify-center rounded-lg gradient-primary px-6 py-2 text-sm font-medium text-primary-foreground hover:shadow-lg transition-all duration-300">
              Chat with Legal Assistant
            </button>
          </a>
        </div>
      </div>
    </Layout>
  );
};

export default RightsPage;