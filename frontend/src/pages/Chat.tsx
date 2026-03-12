import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2 } from "lucide-react";
import Layout from "../components/Layout";

interface Message {
  id: string;
  text: string;
  sender: "user" | "bot";
  timestamp: Date;
  language?: string;
}

const ChatPage = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      text: "Hello! I'm your Smart Legal Assistant. I can help you understand legal matters, explain your rights, and provide guidance on legal documents. How can I assist you today?",
      sender: "bot",
      timestamp: new Date(),
      language: "en",
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
  
  const handleSend = async () => {
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
    
    try {
      // Call the backend /query endpoint with multilingual support
      const response = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: inputText,
          // Language will be auto-detected by the backend
        }),
      });
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Format the bot response
      const suggestions = data.suggestions && data.suggestions.length > 0 
        ? data.suggestions.join("\n")
        : "";
      
      const laws = data.laws && data.laws.length > 0
        ? "**Relevant Laws:**\n" + data.laws.join("\n")
        : "";
      
      const botResponseText = `${data.summary}\n\n${laws}${laws ? "\n\n" : ""}${suggestions ? "**Suggestions:**\n" + suggestions : ""}`;
      
      const botResponse: Message = {
        id: (Date.now() + 1).toString(),
        text: botResponseText.trim(),
        sender: "bot",
        timestamp: new Date(),
        language: data.language,
      };
      
      setMessages(prev => [...prev, botResponse]);
    } catch (error) {
      console.error("Error calling backend API:", error);
      
      // Fallback error message
      const errorResponse: Message = {
        id: (Date.now() + 1).toString(),
        text: "I apologize, but I'm unable to connect to the legal assistant service at the moment. Please ensure the backend server is running on http://localhost:8000 and try again.",
        sender: "bot",
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, errorResponse]);
    }
    
    setIsTyping(false);
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
            Ask any legal question in any language and get instant guidance
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
                    <div className="flex items-center justify-between mt-2 gap-4">
                      <p className={`text-xs ${
                        message.sender === "user" ? "text-primary-foreground/70" : "text-muted-foreground"
                      }`}>
                        {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </p>
                      {message.language && message.sender === "bot" && (
                        <p className={`text-xs px-2 py-1 rounded ${
                          message.sender === "user" 
                            ? "bg-primary-foreground/20" 
                            : "bg-primary/10 text-primary"
                        }`}>
                          Language: {message.language}
                        </p>
                      )}
                    </div>
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