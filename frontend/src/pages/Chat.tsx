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

// Language-aware translations for response headers
const languageLabels: Record<string, { laws: string; suggestions: string }> = {
  en: { laws: "Relevant Laws:", suggestions: "Suggestions:" },
  hi: { laws: "प्रासंगिक कानून:", suggestions: "सुझाव:" },
  bn: { laws: "প্রাসঙ্গিক আইন:", suggestions: "পরামর্শ:" },
  ta: { laws: "தொடர்புடைய சட்டங்கள்:", suggestions: "பரামर்शங்கள்:" },
  te: { laws: "సంబంధిత చట్టాలు:", suggestions: "సూచనలు:" },
  mr: { laws: "संबंधित कानून:", suggestions: "सुझाव:" },
  gu: { laws: "સંબંધિત કાયદો:", suggestions: "સૂચનો:" },
  kn: { laws: "ಸಂಬಂಧಿತ ಕಾನೂನುಗಳು:", suggestions: "ಸಲಹೆಗಳು:" },
  ml: { laws: "പ്രാസঙ്ഗിക നിയമങ്ങൾ:", suggestions: "നിർദ്ദേശങ്ങൾ:" },
  pa: { laws: "ਸੰਬੰਧਿਤ ਕਾਨੂੰਨ:", suggestions: "ਮੁਲਾਂਕਣ:" },
};

const ChatPage = () => {
  useEffect(() => {
  window.scrollTo({
    top: 0,
    behavior: "auto"
  });
}, []);
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
  const isFirstLoad = useRef(true);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    chatContainerRef.current?.scrollTo({
      top: 0,
      behavior: "auto"
    });
  }, []);

  useEffect(() => {
    if (isFirstLoad.current) {
      isFirstLoad.current = false;
      return;
    }

    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!inputText.trim()) return;

    // Store the input text before clearing it (since setState is asynchronous)
    const queryText = inputText;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: queryText,
      sender: "user",
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText("");
    setIsTyping(true);

    try {
      // Call the backend /query endpoint with multilingual support
      const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: queryText,  // ← Now uses stored value, not empty state
          // Language will be auto-detected by the backend
        }),
      });

      if (!response.ok) {
        const errorStatus = response.status;
        let errorMessage = "I apologize, but I'm unable to process your request at the moment.";

        if (errorStatus === 401 || errorStatus === 403) {
          errorMessage = "Authentication error. Please contact support.";
        } else if (errorStatus === 404) {
          errorMessage = "The service endpoint was not found. Please ensure the backend is properly configured.";
        } else if (errorStatus === 429) {
          errorMessage = "Too many requests. Please wait a moment before trying again.";
        } else if (errorStatus === 500 || errorStatus === 502 || errorStatus === 503) {
          errorMessage = "The legal assistant service is experiencing issues. Please try again later.";
        } else if (errorStatus === 504) {
          errorMessage = "The service is taking too long to respond. Please try again.";
        }

        throw new Error(`API Error ${errorStatus}: ${errorMessage}`);
      }

      const data = await response.json();

      // Type validation for response
      if (!data || typeof data.summary !== "string") {
        throw new Error("Invalid response format from backend");
      }

      // Get language-specific labels
      const detectedLanguage = typeof data.language === "string" ? data.language : "en";
      const labels = languageLabels[detectedLanguage] || languageLabels["en"];

      // Format the bot response with language-aware labels
      const suggestions = Array.isArray(data.suggestions) && data.suggestions.length > 0
        ? data.suggestions.join("\n")
        : "";

      const laws = Array.isArray(data.laws) && data.laws.length > 0
        ? `**${labels.laws}**\n` + data.laws.join("\n")
        : "";

      const botResponseText = `${data.summary}\n\n${laws}${laws ? "\n\n" : ""}${suggestions ? `**${labels.suggestions}**\n` + suggestions : ""}`;

      const botResponse: Message = {
        id: (Date.now() + 1).toString(),
        text: botResponseText.trim(),
        sender: "bot",
        timestamp: new Date(),
        language: detectedLanguage,
      };

      setMessages(prev => [...prev, botResponse]);
    } catch (error) {
      console.error("Error calling backend API:", error);

      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";

      // Fallback error message
      const errorResponse: Message = {
        id: (Date.now() + 1).toString(),
        text: `I apologize, but I encountered an error: ${errorMessage}\n\nPlease ensure the backend server is running on ${import.meta.env.VITE_API_URL || "http://localhost:8000"} and try again.`,
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
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="text-center mb-8 animate-fade-up">
          <h1 className="text-4xl font-bold text-foreground mb-4">
            Legal Assistant Chat
          </h1>
          <p className="text-lg text-muted-foreground">
            Ask any legal question in any language and get instant guidance
          </p>
        </div>

        <div className="border-2 border-black rounded-xl bg-card shadow-lg animate-fade-up overflow-hidden">
          {/* Chat Messages */}
          <div
            ref={chatContainerRef}
            className="h-[350px] overflow-y-auto p-6 space-y-4 scrollbar-thin"
          >
            {messages.map((message, index) => (
              <div
                key={message.id}
                className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"} animate-fade-up`}
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                <div className={`flex max-w-[80%] ${message.sender === "user" ? "flex-row-reverse" : "flex-row"} items-start space-x-2`}>
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${message.sender === "user" ? "gradient-primary ml-2" : "bg-secondary mr-2"
                    }`}>
                    {message.sender === "user" ? (
                      <User className="h-4 w-4 text-primary-foreground" />
                    ) : (
                      <Bot className="h-4 w-4 text-secondary-foreground" />
                    )}
                  </div>

                  <div className={`rounded-lg px-4 py-3 ${message.sender === "user"
                      ? "gradient-primary text-primary-foreground"
                      : "bg-muted text-foreground"
                    }`}>
                    <p className="text-sm whitespace-pre-wrap">{message.text}</p>
                    <div className="flex items-center justify-between mt-2 gap-4">
                      <p className={`text-xs ${message.sender === "user" ? "text-primary-foreground/70" : "text-muted-foreground"
                        }`}>
                        {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </p>
                      {message.language && message.sender === "bot" && (
                        <p className={`text-xs px-2 py-1 rounded ${message.sender === "user"
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