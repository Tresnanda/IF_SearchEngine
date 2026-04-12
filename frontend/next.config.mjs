/** @type {import('next').NextConfig} */
const nextConfig = {
    rewrites: async () => {
        const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:5000';
        console.log('Using Backend URL:', backendUrl);
        return [
            {
                source: '/api/:path*',
                destination: `${backendUrl}/:path*`, // Proxy to Backend
            },
            {
                source: '/files/:path*',
                destination: `${backendUrl}/files/:path*`, // Proxy to Backend
            },
        ]
    },
};

export default nextConfig;
