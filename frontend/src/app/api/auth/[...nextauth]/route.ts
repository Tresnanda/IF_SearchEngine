import NextAuth, { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "IMISSU Dummy",
      credentials: {
        email: { label: "Email", type: "text", placeholder: "admin@informatika.unud.ac.id" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        // Dummy check for now. Will be replaced by real OAuth.
        if (credentials?.email === "admin@informatika.unud.ac.id" && credentials?.password === "password") {
          return { id: "1", name: "Admin", email: "admin@informatika.unud.ac.id", role: "admin" };
        }
        return null;
      }
    })
  ],
  pages: {
    signIn: '/login',
  },
  session: {
    strategy: "jwt",
  },
  secret: process.env.NEXTAUTH_SECRET || "super-secret-key-replace-in-production",
};

const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };
