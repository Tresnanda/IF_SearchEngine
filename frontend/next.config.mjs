/** @type {import('next').NextConfig} */
const nextConfig = {
    rewrites: async () => {
        const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:5000';
        console.log('Using Backend URL:', backendUrl);
        return [
            {
                source: '/api/search',
                destination: `${backendUrl}/search`,
            },
            {
                source: '/api/feedback',
                destination: `${backendUrl}/feedback`,
            },
            {
                source: '/files/:path*',
                destination: `${backendUrl}/files/:path*`, // Proxy to Backend
            },
        ]
    },
};

export default nextConfig;
