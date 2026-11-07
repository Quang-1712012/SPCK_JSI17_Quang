// MineOS Firebase initialization (Firebase Web SDK modular v11).
// Replace the placeholder values with your Firebase project's web app config.
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.0.2/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/11.0.2/firebase-auth.js";

const firebaseConfig = {
    apiKey: "AIzaSyABFLXc-ayySRWUGmCcU2xns3b8FJxza-Y",
    authDomain: "mineos-318b7.firebaseapp.com",
    projectId: "mineos-318b7",
    storageBucket: "mineos-318b7.firebasestorage.app",
    messagingSenderId: "75424543206",
    appId: "1:75424543206:web:1d5eef60031ba785faa627",
    measurementId: "G-JR1NPP1XL7"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
