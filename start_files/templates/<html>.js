<html>
    
</html>

<script>
        // Function to load all contacts from the database
        async function loadContacts() {
            console.log('loadContacts function called');
            try {
                console.log('Fetching contacts...');
                const response = await fetch('/create_contacts/');
                console.log('Fetch response:', response);
                
                if (!response.ok) {
                    throw new Error(`Failed to fetch contacts: ${response.status} ${response.statusText}`);
                }

                const contacts = await response.json();
                console.log('Contacts received:', contacts);
                displayContacts(contacts);
            } catch (error) {
                console.error('Error loading contacts:', error);
                document.getElementById('contact-list').innerHTML = `<p>Error loading contacts: ${error.message}</p>`;
                clearContactDetails();  // Clear details on error
            }
        }

        // Function to display contacts in the view box
        function displayContacts(contacts) {
            console.log('displayContacts function called with:', contacts);
            const contactList = document.getElementById('contact-list');
            contactList.innerHTML = '<h3>Contacts</h3>'; // Reset the list with the header

            if (contacts.length === 0) {
                contactList.innerHTML += '<p>No contacts found.</p>';
                clearContactDetails(); // Clear details when no contacts
                return;
            }

            contacts.forEach(contact => {
                const contactItem = document.createElement('div');
                contactItem.className = 'contact-item';
                
                const nameSpan = document.createElement('span');
                nameSpan.className = 'contact-name';
                nameSpan.innerText = contact.name;
                
                const deleteButton = document.createElement('button');
                deleteButton.className = 'delete-btn';
                deleteButton.innerText = 'Delete';
                deleteButton.onclick = function(e) {
                    e.stopPropagation(); // Prevent triggering the contact item click
                    deleteContact(contact.id);
                };

                contactItem.appendChild(nameSpan);
                contactItem.appendChild(deleteButton);

                // Show contact details on click
                contactItem.onclick = function() {
                    document.getElementById('details-email').innerText = contact.email;
                    document.getElementById('extra-notes').value = contact.notes;
                    document.getElementById('contact-details').style.display = 'block';
                };

                contactList.appendChild(contactItem);
            });
            console.log('Contacts displayed in the list');
        }

        // Function to clear contact details
        function clearContactDetails() {
            document.getElementById('details-email').innerText = '';
            document.getElementById('extra-notes').value = '';
            document.getElementById('contact-details').style.display = 'none';
        }

        // Function to add a new contact to the database
        document.getElementById('add-contact').onclick = async function() {
            console.log('Add contact button clicked');
            const name = document.getElementById('name').value;
            const email = document.getElementById('email').value;
            const notes = document.getElementById('notes').value;

            try {
                console.log('Sending new contact data:', { name, email, notes });
                const response = await fetch('/create_contacts/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, notes })
                });

                if (!response.ok) {
                    throw new Error(`Failed to add contact: ${response.status} ${response.statusText}`);
                }
                
                const newContact = await response.json();
                console.log('New contact added:', newContact);
                loadContacts(); // Refresh the contact list
                
                // Clear input fields after saving
                document.getElementById('name').value = '';
                document.getElementById('email').value = '';
                document.getElementById('notes').value = '';
            } catch (error) {
                console.error('Error adding contact:', error);
                alert(`Failed to add contact: ${error.message}`);
            }
        };

        // Function to delete a contact
        async function deleteContact(contactId) {
            try {
                const response = await fetch(`/delete_contact/${contactId}/`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    throw new Error(`Failed to delete contact: ${response.status} ${response.statusText}`);
                }

                console.log(`Contact ${contactId} deleted successfully`);
                loadContacts(); // Refresh the contact list
            } catch (error) {
                console.error('Error deleting contact:', error);
                alert(`Failed to delete contact: ${error.message}`);
            }
        }

        // Function to save additional notes
// Function to save additional notes
document.getElementById('save-notes').onclick = async function() {
    const email = document.getElementById('details-email').innerText;
    const extraNotes = document.getElementById('extra-notes').value;

    // Extract the contact ID based on the email, or modify your logic as needed
    const contactId = await getContactIdByEmail(email); // You will need to implement this

    if (!contactId) {
        alert("Contact not found.");
        return;
    }

    try {
        const response = await fetch(`/update_contact/${contactId}/`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: extraNotes })
        });

        if (!response.ok) {
            throw new Error(`Failed to save notes: ${response.status} ${response.statusText}`);
        }

        const updatedContact = await response.json();
        console.log('Notes saved for:', updatedContact);
        alert('Notes saved successfully!'); // Placeholder alert
    } catch (error) {
        console.error('Error saving notes:', error);
        alert(`Failed to save notes: ${error.message}`);
    }
};

// Function to get the contact ID by email
async function getContactIdByEmail(email) {
    const response = await fetch('/create_contacts/');
    const contacts = await response.json();
    const contact = contacts.find(contact => contact.email === email);
    return contact ? contact.id : null;
}


        // Load contacts when the page loads
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOMContentLoaded event fired');
            loadContacts();
        });

        // Additional check to ensure loadContacts is called
        console.log('Script loaded, calling loadContacts immediately');
        loadContacts();
    </script>
<