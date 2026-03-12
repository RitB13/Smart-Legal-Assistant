import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2 } from "lucide-react";
import Layout from "../components/Layout";

interface Message {
  id: string;
  text: string;
  sender: "user" | "bot";
  timestamp: Date;
}

const ChatPage = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      text: "Hello! I'm your Smart Legal Assistant. I can help you understand legal matters, explain your rights, and provide guidance on legal documents. How can I assist you today?",
      sender: "bot",
      timestamp: new Date(),
    }
  ]);
  const [inputText, setInputText] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  const generateBotResponse = (userMessage: string): string => {
    const lowerMessage = userMessage.toLowerCase();
    
    if (lowerMessage.includes("rent") || lowerMessage.includes("tenant") || lowerMessage.includes("landlord")) {
      return "Regarding rental/tenancy matters:\n\n1. **Tenant Rights:** You have the right to a habitable living space, privacy, and return of security deposit.\n\n2. **Landlord Obligations:** Must maintain property, provide proper notice before entry (usually 24-48 hours), and follow legal eviction procedures.\n\n3. **Important:** Always get agreements in writing and keep records of all payments.\n\nWould you like more specific information about any of these points?";
    }
    
    if (lowerMessage.includes("divorce") || lowerMessage.includes("marriage")) {
      return "For matrimonial matters:\n\n1. **Grounds for Divorce:** Mutual consent, cruelty, desertion, adultery, mental illness, etc.\n\n2. **Rights:** Both parties have rights to property division, child custody consideration, and maintenance.\n\n3. **Process:** Consider mediation first, file petition in family court, attend counseling sessions.\n\nI recommend consulting a family law attorney for personalized advice. Need information on any specific aspect?";
    }
    
    if (lowerMessage.includes("consumer") || lowerMessage.includes("refund") || lowerMessage.includes("product")) {
      return "Consumer Rights Information:\n\n1. **Right to Safety:** Protection against hazardous goods\n2. **Right to Information:** Full product details must be provided\n3. **Right to Choose:** Freedom to select products\n4. **Right to Redressal:** Compensation for defective products\n\nYou can file complaints at consumer forums. Time limit is usually 2 years from purchase date. What specific issue are you facing?";
    }
    
    if (lowerMessage.includes("employment") || lowerMessage.includes("job") || lowerMessage.includes("salary")) {
      return "Employment Law Guidance:\n\n1. **Minimum Wages:** Employer must pay at least minimum wage as per state regulations\n2. **Working Hours:** Standard is 8-9 hours per day with overtime pay\n3. **Leave Entitlements:** Casual leave, sick leave, earned leave as per company policy\n4. **Termination:** Proper notice period must be given (usually 30-90 days)\n\nDo you have a specific employment concern I can help with?";
    }
    
    return "I understand your query. Based on my knowledge:\n\n1. **Document everything:** Keep written records of all legal matters\n2. **Know deadlines:** Legal matters often have strict time limits\n3. **Seek professional help:** Complex matters require qualified legal counsel\n\nCould you provide more specific details about your legal question? This will help me give you more targeted guidance.";
  };
  
  const handleSend = () => {
    if (!inputText.trim()) return;
    
    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      sender: "user",
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputText("");
    setIsTyping(true);
    
    // Simulate bot response
    setTimeout(() => {
      const botResponse: Message = {
        id: (Date.now() + 1).toString(),
        text: generateBotResponse(inputText),
        sender: "bot",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, botResponse]);
      setIsTyping(false);
    }, 1500);
  };
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  
  return (
    <Layout>
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="text-center mb-8 animate-fade-up">
          <h1 className="text-4xl font-bold text-foreground mb-4">
            Legal Assistant Chat
          </h1>
          <p className="text-lg text-muted-foreground">
            Ask any legal question and get instant guidance
          </p>
        </div>
        
        <div className="border border-border rounded-xl bg-card shadow-lg animate-fade-up" style={{ animationDelay: "0.1s" }}>
          {/* Chat Messages */}
          <div className="h-[500px] overflow-y-auto p-6 space-y-4">
            {messages.map((message, index) => (
              <div
                key={message.id}
                className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"} animate-fade-up`}
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                <div className={`flex max-w-[80%] ${message.sender === "user" ? "flex-row-reverse" : "flex-row"} items-start space-x-2`}>
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    message.sender === "user" ? "gradient-primary ml-2" : "bg-secondary mr-2"
                  }`}>
                    {message.sender === "user" ? (
                      <User className="h-4 w-4 text-primary-foreground" />
                    ) : (
                      <Bot className="h-4 w-4 text-secondary-foreground" />
                    )}
                  </div>
                  
                  <div className={`rounded-lg px-4 py-3 ${
                    message.sender === "user"
                      ? "gradient-primary text-primary-foreground"
                      : "bg-muted text-foreground"
                  }`}>
                    <p className="text-sm whitespace-pre-wrap">{message.text}</p>
                    <p className={`text-xs mt-1 ${
                      message.sender === "user" ? "text-primary-foreground/70" : "text-muted-foreground"
                    }`}>
                      {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                </div>
              </div>
            ))}
            
            {isTyping && (
              <div className="flex justify-start animate-fade-up">
                <div className="flex items-start space-x-2">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                    <Bot className="h-4 w-4 text-secondary-foreground" />
                  </div>
                  <div className="bg-muted rounded-lg px-4 py-3">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
          
          {/* Input Section */}
          <div className="border-t border-border p-4">
            <div className="flex space-x-2">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your legal question here..."
                className="flex-1 px-4 py-2 rounded-lg border border-input bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-all"
              />
              <button
                onClick={handleSend}
                disabled={!inputText.trim() || isTyping}
                className="inline-flex items-center justify-center rounded-lg gradient-primary px-4 py-2 text-primary-foreground hover:shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isTyping ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default ChatPage;