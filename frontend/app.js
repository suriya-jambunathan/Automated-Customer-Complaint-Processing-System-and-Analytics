// AWS Cognito configuration
AWSCognito.config.region = 'us-east-1'; // e.g., us-east-1
AWSCognito.config.credentials = new AWS.CognitoIdentityCredentials({
    IdentityPoolId: 'us-east-1:d8040203-38a3-4658-a876-4d660cecfdf0'
});

var poolData = {
    UserPoolId: 'us-east-1_d7F4Iv2nd',
    ClientId: '6ef9rf4u39salgovd85rnqgqq8'
};
var userPool = new AWSCognito.CognitoIdentityServiceProvider.CognitoUserPool(poolData);

// Sign-up function
function signUp() {
    var email = document.getElementById('signupEmail').value;
    var password = document.getElementById('signupPassword').value;

    var attributeList = [];
    var dataEmail = {
        Name: 'email',
        Value: email
    };

    var attributeEmail = new AWSCognito.CognitoIdentityServiceProvider.CognitoUserAttribute(dataEmail);
    attributeList.push(attributeEmail);

    userPool.signUp(email, password, attributeList, null, function(err, result) {
        if (err) {
            alert(err.message || JSON.stringify(err));
            return;
        }
        var cognitoUser = result.user;
        console.log('user name is ' + cognitoUser.getUsername());
    });
}

// Login function
function login() {
    var email = document.getElementById('loginEmail').value;
    var password = document.getElementById('loginPassword').value;

    var authenticationData = {
        Username: email,
        Password: password,
    };
    var authenticationDetails = new AWSCognito.CognitoIdentityServiceProvider.AuthenticationDetails(authenticationData);

    var userData = {
        Username: email,
        Pool: userPool
    };
    var cognitoUser = new AWSCognito.CognitoIdentityServiceProvider.CognitoUser(userData);

    cognitoUser.authenticateUser(authenticationDetails, {
        onSuccess: function(result) {
            console.log('access token + ' + result.getAccessToken().getJwtToken());
            // Use the token for your app, redirect to dashboard etc.
        },
        onFailure: function(err) {
            alert(err.message || JSON.stringify(err));
        },
    });
}
