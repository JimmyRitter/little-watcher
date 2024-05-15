# little-watcher
Raspberry Pi + Azure IoT solution to keep an eye on what's happening when you are not around


needed for `GPIO.add_event_detect`:
`sudo apt install python3-rpi-lgpio`

run `python motion.py` to execute picture/video recording

needed to run:
`pip install python-dotenv`
`pip install azure-communication-email`
`pip install boto3` <!-- AWS SDK -->



BEFORE RUNNING TERRAFORM FILE, NEED SOME MANUAL STEPS
Since an email needs to be sent when a record is created,
we need a domain to be used by Simple Email Service (AWS SES).

AWS WorkMail currently gives us a "free domain" with an AWS extension,
that can be used along with SES.


Before running `terraform plan` or `terraform apply`,  you need to login to AWS portal,
navigate to service AWS WorkMail.
Be careful which region is selected. Be sure to select the right one.
First step is create an organization. (This is not currently available on Terraform).
Pick the "free test domain" and choose a name.
Create at and keep track of the chosen name. You will need it soon.

Next step is to create a new account within the new domain, and verify it.
Create it on "Users" tab, and we are using it's username as "Sender", so it will be "sender@yourawsdomain.com".
Open the mail UI (<organization_name_created_few_minutes_ago>.awsapps.com/mail).
<!-- Now SES (on terraform script) should handle the email verification send. -->
Now run the terraform script,  that should handle the trigger of email verifications.
On the mail UI, click to confirm on the received email.

Since we are using the free domain, it allows us to have just one receiver email.
You will need to log to this email (configured on .env) to also confirm you are the email owner.

Now that the domain manual step was done, the terraform script was run, you can run the `motion.py` script.