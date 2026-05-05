public with sharing class RestClient {
    public enum HttpVerb {
        GET,
        POST,
        PUT,
        PATCH,
        DEL
    }

    public static HttpResponse makeApiCall(
        String namedCredential,
        HttpVerb method,
        String path
    ) {
        HttpRequest request = new HttpRequest();
        request.setEndpoint('callout:' + namedCredential + '/' + path);
        request.setMethod(method.name());
        return new Http().send(request);
    }
}
