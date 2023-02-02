
## Run in local jenkins

1. Download Jenkins:
```shell
brew install jenkins-lts
```
2. Check that Jenkins is runnning at http://localhost:8080/
3. Setup user and install recommended plugins
4. Moreover install Docker and Docker Pipeline plugins
5. Restart jenkins and log in
5. Create new Pipeline
   - Check 'Github Project': https://github.com/Vandebron/mpyl
     - Select Pipeline script from SCM:
       - Add repo url
       - Set branch specifier to `/main` and script path to `Jenkinsfile`
6. Click save
7. Edit and add docker to Jenkins' PATH at `/opt/homebrew/Cellar/jenkins-lts/2.375.2/homebrew.mxcl.jenkins-lts.plist`:
```xml
<key>EnvironmentVariables</key>
<dict>
<key>PATH</key>
<string>/opt/homebrew/bin/:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Applications/Docker.app/Contents/Resources/bin/</string>
</dict>
```
8. Run docker daemon
9. Run pipeline