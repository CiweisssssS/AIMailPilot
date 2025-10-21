import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle, CheckCircle2, Copy, ExternalLink } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useState, useEffect } from "react";

export default function SetupHelp() {
  const { toast } = useToast();
  const [redirectUri, setRedirectUri] = useState("");

  useEffect(() => {
    // Get the current URL to show the exact redirect URI needed
    const currentDomain = window.location.origin;
    setRedirectUri(`${currentDomain}/auth/google/callback`);
  }, []);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: "Copied!",
      description: "Redirect URI copied to clipboard",
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/5 to-purple-500/5 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">Google OAuth Setup Guide</CardTitle>
            <CardDescription>
              Follow these steps to configure Google OAuth for Gmail access
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-yellow-900">Configuration Required</h3>
                  <p className="text-sm text-yellow-800 mt-1">
                    You need to set up OAuth credentials in Google Cloud Console before you can use this application.
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="font-semibold text-lg flex items-center gap-2">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary text-white text-sm">1</span>
                Create Google Cloud Project
              </h3>
              <div className="ml-8 space-y-2">
                <p className="text-sm text-muted-foreground">
                  Go to <a href="https://console.cloud.google.com/" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline inline-flex items-center gap-1">
                    Google Cloud Console <ExternalLink className="h-3 w-3" />
                  </a>
                </p>
                <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                  <li>Create a new project or select an existing one</li>
                  <li>Note your project name for reference</li>
                </ul>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="font-semibold text-lg flex items-center gap-2">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary text-white text-sm">2</span>
                Enable Gmail API
              </h3>
              <div className="ml-8 space-y-2">
                <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                  <li>Navigate to "APIs & Services" → "Library"</li>
                  <li>Search for "Gmail API"</li>
                  <li>Click "Enable"</li>
                </ul>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="font-semibold text-lg flex items-center gap-2">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary text-white text-sm">3</span>
                Create OAuth 2.0 Credentials
              </h3>
              <div className="ml-8 space-y-2">
                <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                  <li>Go to "APIs & Services" → "Credentials"</li>
                  <li>Click "Create Credentials" → "OAuth client ID"</li>
                  <li>Application type: <strong>Web application</strong></li>
                  <li>Name: "AI Email Intelligence" (or any name you prefer)</li>
                </ul>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="font-semibold text-lg flex items-center gap-2">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary text-white text-sm">4</span>
                Configure Authorized Redirect URI
              </h3>
              <div className="ml-8 space-y-3">
                <p className="text-sm text-muted-foreground">
                  Under "Authorized redirect URIs", click "Add URI" and paste this exact URL:
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 bg-muted p-3 rounded-lg text-sm font-mono break-all">
                    {redirectUri || "Loading..."}
                  </code>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => copyToClipboard(redirectUri)}
                    disabled={!redirectUri}
                    data-testid="button-copy-redirect-uri"
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  ⚠️ The URI must match exactly, including the protocol (https://)
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="font-semibold text-lg flex items-center gap-2">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary text-white text-sm">5</span>
                Copy Credentials to Replit
              </h3>
              <div className="ml-8 space-y-2">
                <p className="text-sm text-muted-foreground">
                  After creating the OAuth client, Google will show you:
                </p>
                <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                  <li><strong>Client ID</strong> - Copy this value</li>
                  <li><strong>Client secret</strong> - Copy this value</li>
                </ul>
                <p className="text-sm text-muted-foreground mt-3">
                  In Replit, open the "Secrets" panel and add:
                </p>
                <div className="bg-muted p-3 rounded-lg space-y-2 text-sm font-mono">
                  <div>GOOGLE_CLIENT_ID = <span className="text-muted-foreground">[paste your Client ID]</span></div>
                  <div>GOOGLE_CLIENT_SECRET = <span className="text-muted-foreground">[paste your Client Secret]</span></div>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="font-semibold text-lg flex items-center gap-2">
                <CheckCircle2 className="h-6 w-6 text-green-600" />
                You're All Set!
              </h3>
              <div className="ml-8 space-y-2">
                <p className="text-sm text-muted-foreground">
                  After completing the setup:
                </p>
                <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                  <li>The application will automatically restart</li>
                  <li>Click "Sign in with Google" on the home page</li>
                  <li>Authorize the app to access your Gmail</li>
                  <li>Start analyzing your emails!</li>
                </ul>
              </div>
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded">
              <h4 className="font-semibold text-blue-900 mb-2">Testing vs Production</h4>
              <p className="text-sm text-blue-800">
                If you see "This app isn't verified" during testing, click "Advanced" → "Go to [app name] (unsafe)". 
                For production use, submit your app to Google for verification.
              </p>
            </div>

            <div className="flex gap-3">
              <Button asChild className="flex-1">
                <a href="/">Back to Home</a>
              </Button>
              <Button asChild variant="outline" className="flex-1">
                <a href="https://console.cloud.google.com/" target="_blank" rel="noopener noreferrer">
                  Open Google Cloud Console <ExternalLink className="h-4 w-4 ml-2" />
                </a>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
