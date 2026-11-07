import { auth } from "./fire_base.js";
import {
    createUserWithEmailAndPassword,
    updateProfile,
    signInWithEmailAndPassword,
    GoogleAuthProvider,
    signInWithPopup,
    sendPasswordResetEmail,
    onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/11.0.2/firebase-auth.js";

const $ = (id) => document.getElementById(id);

function showMessage(id, message, type = "") {
    const element = $(id);
    if (!element) return;
    element.textContent = message;
    element.className = `form-message ${type}`.trim();
}

function friendlyError(error) {
    const messages = {
        "auth/invalid-email": "Địa chỉ email không hợp lệ.",
        "auth/user-not-found": "Không tìm thấy tài khoản với email này.",
        "auth/wrong-password": "Email hoặc mật khẩu không chính xác.",
        "auth/invalid-credential": "Email hoặc mật khẩu không chính xác.",
        "auth/email-already-in-use": "Email này đã được đăng ký.",
        "auth/weak-password": "Mật khẩu chưa đủ mạnh. Hãy dùng ít nhất 6 ký tự.",
        "auth/too-many-requests": "Bạn thử quá nhiều lần. Hãy đợi một lúc rồi thử lại.",
        "auth/popup-closed-by-user": "Cửa sổ đăng nhập Google đã bị đóng.",
        "auth/popup-blocked": "Trình duyệt đã chặn cửa sổ bật lên. Hãy cho phép popup rồi thử lại.",
        "auth/unauthorized-domain": "Tên miền hiện tại chưa được thêm vào Authorized domains trong Firebase.",
        "auth/network-request-failed": "Lỗi mạng. Hãy kiểm tra kết nối Internet."
    };
    return messages[error.code] || `Không thể thực hiện thao tác (${error.code || "unknown"}). Hãy kiểm tra cấu hình Firebase.`;
}

function setBusy(form, busy, label) {
    const button = form?.querySelector('button[type="submit"]');
    if (!button) return;
    button.disabled = busy;
    const text = button.querySelector("span");
    if (text) text.textContent = busy ? label : button.dataset.originalLabel;
}

document.querySelectorAll('button[data-toggle-password]').forEach((button) => {
    button.addEventListener("click", () => {
        const input = $(button.dataset.togglePassword);
        if (!input) return;
        const reveal = input.type === "password";
        input.type = reveal ? "text" : "password";
        button.textContent = reveal ? "Ẩn" : "Hiện";
        button.setAttribute("aria-label", reveal ? "Ẩn mật khẩu" : "Hiện mật khẩu");
    });
});

const loginForm = $("login-form");
if (loginForm) {
    const submit = loginForm.querySelector('button[type="submit"]');
    submit.dataset.originalLabel = submit.querySelector("span").textContent;

    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        showMessage("login-message", "");
        setBusy(loginForm, true, "Đang đăng nhập...");
        const email = $("login-email").value.trim();
        const password = $("login-password").value;

        try {
            await signInWithEmailAndPassword(auth, email, password);
            showMessage("login-message", "Đăng nhập thành công! Đang chuyển trang...", "success");
            // Change this destination to your actual MineOS home page.
            window.location.href = "index.html";
        } catch (error) {
            showMessage("login-message", friendlyError(error), "error");
        } finally {
            setBusy(loginForm, false);
        }
    });

    $("forgot-password").addEventListener("click", async () => {
        const email = $("login-email").value.trim();
        if (!email) {
            showMessage("login-message", "Nhập email vào ô Email trước, rồi chọn Quên mật khẩu.", "error");
            $("login-email").focus();
            return;
        }
        try {
            await sendPasswordResetEmail(auth, email);
            showMessage("login-message", "Nếu email thuộc tài khoản hợp lệ, hướng dẫn đặt lại mật khẩu sẽ được gửi đến email đó.", "success");
        } catch (error) {
            showMessage("login-message", friendlyError(error), "error");
        }
    });
}

const signupForm = $("signup-form");
if (signupForm) {
    const submit = signupForm.querySelector('button[type="submit"]');
    submit.dataset.originalLabel = submit.querySelector("span").textContent;

    signupForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        showMessage("signup-message", "");

        const displayName = $("signup-name").value.trim();
        const email = $("signup-email").value.trim();
        const password = $("signup-password").value;
        const confirmPassword = $("signup-confirm").value;

        if (password !== confirmPassword) {
            showMessage("signup-message", "Mật khẩu xác nhận không khớp.", "error");
            $("signup-confirm").focus();
            return;
        }

        setBusy(signupForm, true, "Đang tạo tài khoản...");
        try {
            const credential = await createUserWithEmailAndPassword(auth, email, password);
            if (displayName) await updateProfile(credential.user, { displayName });
            showMessage("signup-message", "Tạo tài khoản thành công! Đang chuyển trang...", "success");
            // Change this destination to your actual MineOS home page.
            window.location.href = "index.html";
        } catch (error) {
            showMessage("signup-message", friendlyError(error), "error");
        } finally {
            setBusy(signupForm, false);
        }
    });
}

const provider = new GoogleAuthProvider();

async function googleSignIn(messageId, button) {
    showMessage(messageId, "");
    button.disabled = true;
    try {
        await signInWithPopup(auth, provider);
        window.location.href = "index.html";
    } catch (error) {
        showMessage(messageId, friendlyError(error), "error");
    } finally {
        button.disabled = false;
    }
}

$("google-login")?.addEventListener("click", (event) => googleSignIn("login-message", event.currentTarget));
$("google-signup")?.addEventListener("click", (event) => googleSignIn("signup-message", event.currentTarget));

// This callback can be extended to update a shared navbar with user details.
onAuthStateChanged(auth, (user) => {
    document.documentElement.dataset.authState = user ? "signed-in" : "signed-out";
});
