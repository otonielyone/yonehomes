<?php
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $first_name = htmlspecialchars($_POST["first_name"]);
    $last_name = htmlspecialchars($_POST["last_name"]);
    $email = htmlspecialchars($_POST["email"]);
    $phone = htmlspecialchars($_POST["phone"]);
    $general_inquiry = htmlspecialchars($_POST["general_inquiry"]);

    $to = "toni@yone.realtor"; // Replace with your email address
    $subject = "New Contact Form Submission";

    $message = "You have received a new message from your contact form.\n\n";
    $message .= "First Name: $first_name\n";
    $message .= "Last Name: $last_name\n";
    $message .= "Email: $email\n";
    $message .= "Phone: $phone\n";``
    $message .= "General Inquiry:\n$general_inquiry\n";

    $headers = "From: $email";

    if (mail($to, $subject, $message, $headers)) {
        // Redirect to thank you page or display success message
        header("Location: thank_you.php"); // Create a thank_you.php page if needed
        exit();
    } else {
        // Redirect to error page or display error message
        header("Location: error.php"); // Create an error.php page if needed
        exit();
    }
}
?>
