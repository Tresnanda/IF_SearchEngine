import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

const isProduction = process.env.NODE_ENV === "production";
const adminEmail = process.env.ADMIN_EMAIL ?? (isProduction ? undefined : "admin@informatika.unud.ac.id");
const adminPassword = process.env.ADMIN_PASSWORD ?? (isProduction ? undefined : "password");
const nextAuthSecret = process.env.NEXTAUTH_SECRET;
const missingProductionAuthConfig = isProduction && (!adminEmail || !adminPassword || !nextAuthSecret);

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "Admin Credentials",
      credentials: {
        email: {
          label: "Email",
          type: "text",
          placeholder: adminEmail ?? "admin@informatika.unud.ac.id",
        },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!adminEmail || !adminPassword || missingProductionAuthConfig) {
          return null;
        }

        if (credentials?.email === adminEmail && credentials?.password === adminPassword) {
          return {
            id: "1",
            name: "Admin",
            email: adminEmail,
            role: "admin",
          };
        }

        return null;
      },
    }),
  ],
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.role = (user as { role?: string }).role ?? "admin";
      }

      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.role = (token.role as string) ?? "admin";
      }

      return session;
    },
  },
  secret: nextAuthSecret,
};
